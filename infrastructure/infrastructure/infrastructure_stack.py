from aws_cdk import core as cdk, aws_ec2 as ec2, aws_ecs as ecs


class InfrastructureStack(cdk.Stack):
    def __init__(self, scope: cdk.Construct, id: str, vpc_id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        vpc = ec2.Vpc.from_lookup(
            self, "development-vpc", vpc_id=vpc_id, is_default=False
        )

        self.cluster = ecs.Cluster(self, "infrastructure-cluster", vpc=vpc)
