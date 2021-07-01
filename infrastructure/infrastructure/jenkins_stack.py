from aws_cdk import (
    core as cdk,
    aws_ec2 as ec2,
    aws_elasticloadbalancingv2 as elb,
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
            task_image_options={
                "image": ecs.ContainerImage.from_registry("jenkins/jenkins:lts-jdk11"),
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

        # update default health check, because it was throwing failure (503) and draining the ecs-tasks
        self.jenkins_service.target_group.configure_health_check(
            path="/login", healthy_http_codes="200", interval=cdk.Duration.minutes(5)
        )
