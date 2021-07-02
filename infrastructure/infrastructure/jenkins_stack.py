from aws_cdk import (
    core as cdk,
    aws_ec2 as ec2,
    aws_elasticloadbalancingv2 as elb,
    aws_efs as efs,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
)


class JenkinsStack(cdk.Stack):
    def __init__(
        self,
        scope: cdk.Construct,
        construct_id: str,
        cluster: ecs.Cluster,
        props,
        **kwargs
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

        self.jenkins_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self,
            "jenkins-service",
            cluster=cluster,
            cpu=512,
            memory_limit_mib=1024,
            health_check_grace_period=cdk.Duration.minutes(5),
            task_image_options={
                "container_name": "jenkins-controller",
                "image": ecs.ContainerImage.from_registry(props["controller_image"]),
                "container_port": 8080,
                "environment": {"ADMIN_PWD": props["admin_password"]},
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

        file_system.connections.allow_default_port_from(self.jenkins_service.service)
