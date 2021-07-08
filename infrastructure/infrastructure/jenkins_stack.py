from aws_cdk import (
    core as cdk,
    aws_ec2 as ec2,
    aws_elasticloadbalancingv2 as elb,
    aws_efs as efs,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_ecr_assets as ecr_assets,
    aws_iam as iam,
    aws_logs as logs,
)


class JenkinsStack(cdk.Stack):
    def __init__(
        self,
        scope: cdk.Construct,
        construct_id: str,
        cluster: ecs.Cluster,
        props,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        file_system = efs.FileSystem(
            self,
            "jenkins-fs",
            vpc=cluster.vpc,
            performance_mode=efs.PerformanceMode.GENERAL_PURPOSE,
            removal_policy=cdk.RemovalPolicy.DESTROY,
            vpc_subnets=ec2.SubnetSelection(
                subnets=[
                    ec2.Subnet.from_subnet_id(
                        self, "jenkins-efs-subnet-1", props["jenkins_subnet_1"]
                    ),
                    ec2.Subnet.from_subnet_id(
                        self, "jenkins-efs-subnet-2", props["jenkins_subnet_2"]
                    ),
                ]
            ),
        )

        access_point = file_system.add_access_point(
            "jenkins-efs-access-point",
            path="/",
            create_acl=efs.Acl(owner_gid="1000", owner_uid="1000", permissions="755"),
            posix_user=efs.PosixUser(gid="0", uid="0"),
        )

        sg_alb = ec2.SecurityGroup(self, "sg-jenkins-alb", vpc=cluster.vpc)

        alb = elb.ApplicationLoadBalancer(
            self,
            "jenkins-lb",
            vpc=cluster.vpc,
            internet_facing=False,
            vpc_subnets=ec2.SubnetSelection(
                subnets=[
                    ec2.Subnet.from_subnet_id(
                        self, "infrastructure-subnet-1", props["alb_subnet_1"]
                    ),
                    ec2.Subnet.from_subnet_id(
                        self, "infrastructure-subnet-2", props["alb_subnet_2"]
                    ),
                ]
            ),
            security_group=sg_alb,
        )

        sg_jenkins = ec2.SecurityGroup(
            self,
            "JenkinsSecurityGroup",
            vpc=cluster.vpc,
            description="Jenkins Security Group for Controller and Agents",
        )

        sg_jenkins.connections.allow_from(
            other=sg_alb,
            port_range=ec2.Port(
                protocol=ec2.Protocol.TCP,
                string_representation="Jenkins Listener Port",
                from_port=8080,
                to_port=8080,
            ),
            description="Allow connections from Load Balancer Security Group",
        )

        sg_jenkins.connections.allow_internally(
            port_range=ec2.Port(
                protocol=ec2.Protocol.TCP,
                string_representation="Jenkins Listener Port",
                from_port=8080,
                to_port=8080,
            ),
            description="Allow connections from Jenkins Agents in the same Security Group",
        )

        sg_jenkins.connections.allow_internally(
            port_range=ec2.Port(
                protocol=ec2.Protocol.TCP,
                string_representation="Jenkins Agent Port",
                from_port=50000,
                to_port=50000,
            ),
            description="Allow connections from Jenkins Agent on Agent Port(50000)",
        )

        agent_execution_role = iam.Role(
            self,
            "AgentExecutionRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
        )

        agent_execution_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AmazonECSTaskExecutionRolePolicy"
            )
        )

        agent_task_role = iam.Role(
            self,
            "AgentTaskRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
        )

        agent_log_group = logs.LogGroup(
            self,
            "AgentLogGroup",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )

        agent_log_stream = logs.LogStream(
            self,
            "AgentLogStream",
            log_group=agent_log_group,
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )

        self.controller_image = ecr_assets.DockerImageAsset(
            self, "jenkins-controller-image", directory="./docker/jenkins-controller"
        )

        self.jenkins_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self,
            "jenkins-service",
            cluster=cluster,
            cpu=1024,
            memory_limit_mib=2048,
            health_check_grace_period=cdk.Duration.minutes(5),
            task_image_options={
                "container_name": "jenkins-controller",
                "image": ecs.ContainerImage.from_docker_image_asset(
                    self.controller_image
                ),
                "container_port": 8080,
                "environment": {
                    "JAVA_OPTS": "-Djenkins.install.runSetupWizard=false",
                    # https://github.com/jenkinsci/configuration-as-code-plugin/blob/leader/README.md#getting-started
                    "CASC_JENKINS_CONFIG": "/jenkins.yaml",
                    "cluster_arn": cluster.cluster_arn,
                    "aws_region": self.region,
                    "jenkins_url": f"http://{alb.load_balancer_dns_name}/",  # Once, the Jenkins is fully deployed this needs to be updated to container IP Address and Port
                    "admin_password": props["admin_password"],
                    "subnet_ids": f"{props['jenkins_subnet_1']},{props['jenkins_subnet_2']}",
                    "security_group_ids": sg_jenkins.security_group_id,
                    "execution_role_arn": agent_execution_role.role_arn,
                    "task_role_arn": agent_task_role.role_arn,
                    "worker_log_group": agent_log_group.log_group_name,
                    "worker_log_stream_prefix": agent_log_stream.log_stream_name,
                },
            },
            desired_count=1,
            load_balancer=alb,
            task_subnets=ec2.SubnetSelection(
                subnets=[
                    ec2.Subnet.from_subnet_id(
                        self, "jenkins-subnet-1", props["jenkins_subnet_1"]
                    ),
                    ec2.Subnet.from_subnet_id(
                        self, "jenkins-subnet-2", props["jenkins_subnet_2"]
                    ),
                ]
            ),
            security_groups=[sg_jenkins],
        )

        self.jenkins_service.task_definition.add_volume(
            name="jenkins-efs",
            efs_volume_configuration=ecs.EfsVolumeConfiguration(
                file_system_id=file_system.file_system_id,
                authorization_config=ecs.AuthorizationConfig(
                    access_point_id=access_point.access_point_id
                ),
                root_directory="/",
                transit_encryption="ENABLED",
            ),
        )

        self.jenkins_service.task_definition.default_container.add_mount_points(
            ecs.MountPoint(
                container_path="/var/jenkins_home",
                read_only=False,
                source_volume="jenkins-efs",
            )
        )

        self.jenkins_service.task_definition.default_container.add_port_mappings(
            ecs.PortMapping(container_port=50000, host_port=50000)
        )

        # IAM Statements to allow jenkins ecs plugin to talk to ECS as well as the Jenkins cluster #
        self.jenkins_service.service.task_definition.add_to_task_role_policy(
            iam.PolicyStatement(
                actions=[
                    "ecs:RegisterTaskDefinition",
                    "ecs:DeregisterTaskDefinition",
                    "ecs:ListClusters",
                    "ecs:DescribeContainerInstances",
                    "ecs:ListTaskDefinitions",
                    "ecs:DescribeTaskDefinition",
                    "ecs:DescribeTasks",
                ],
                resources=["*"],
            )
        )

        self.jenkins_service.service.task_definition.add_to_task_role_policy(
            iam.PolicyStatement(
                actions=["ecs:ListContainerInstances"], resources=[cluster.cluster_arn]
            )
        )

        self.jenkins_service.service.task_definition.add_to_task_role_policy(
            iam.PolicyStatement(
                actions=["ecs:RunTask"],
                resources=[
                    "arn:aws:ecs:{0}:{1}:task-definition/fargate-agents*".format(
                        self.region,
                        self.account,
                    )
                ],
            )
        )

        self.jenkins_service.service.task_definition.add_to_task_role_policy(
            iam.PolicyStatement(
                actions=["ecs:StopTask"],
                resources=[
                    "arn:aws:ecs:{0}:{1}:task/*".format(self.region, self.account)
                ],
                conditions={
                    "ForAnyValue:ArnEquals": {"ecs:cluster": cluster.cluster_arn}
                },
            )
        )

        self.jenkins_service.service.task_definition.add_to_task_role_policy(
            iam.PolicyStatement(
                actions=["ecs:DescribeTasks"],
                resources=[
                    "arn:aws:ecs:{0}:{1}:task/*".format(self.region, self.account)
                ],
                conditions={
                    "ForAnyValue:ArnEquals": {"ecs:cluster": cluster.cluster_arn}
                },
            )
        )

        self.jenkins_service.service.task_definition.add_to_task_role_policy(
            iam.PolicyStatement(
                actions=["iam:PassRole"],
                resources=[agent_task_role.role_arn, agent_execution_role.role_arn],
            )
        )

        self.jenkins_service.service.task_definition.add_to_task_role_policy(
            iam.PolicyStatement(
                actions=[
                    "logs:DescribeLogStreams",
                    "logs:FilterLogEvents",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                    "logs:GetLogEvents",
                ],
                resources=[agent_log_group.log_group_arn],
            )
        )

        file_system.connections.allow_default_port_from(self.jenkins_service.service)
