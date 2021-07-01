from aws_cdk import core, aws_ec2 as ec2, aws_ram as ram


class NetworkingStack(core.Stack):
    def __init__(self, scope: core.Construct, construct_id: str, props, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.vpc = ec2.Vpc(
            self,
            "acme-network",
            max_azs=2,
            cidr="10.1.0.0/16",
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="public", subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="infrastructure",
                    subnet_type=ec2.SubnetType.PRIVATE,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="jenkins", subnet_type=ec2.SubnetType.PRIVATE, cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="gitlab", subnet_type=ec2.SubnetType.PRIVATE, cidr_mask=24
                ),
            ],
        )

        core.CfnOutput(self, "VpcId", value=self.vpc.vpc_id)

        private_selection = self.vpc.select_subnets(subnet_type=ec2.SubnetType.PRIVATE)
        public_selection = self.vpc.select_subnets(subnet_type=ec2.SubnetType.PUBLIC)

        arns = []
        for subnet in private_selection.subnets:
            arns.append(
                f"arn:aws:ec2:{self.region}:{self.account}:subnet/{subnet.subnet_id}"
            )

        for subnet in public_selection.subnets:
            arns.append(
                f"arn:aws:ec2:{self.region}:{self.account}:subnet/{subnet.subnet_id}"
            )

        ram.CfnResourceShare(
            self,
            id="network",
            name="development",
            principals=[
                f"arn:aws:organizations::{props['management_account']}:ou/{props['root_ou']}/{props['non_production_ou']}",  # Non-Production OU
                f"arn:aws:organizations::{props['management_account']}:ou/{props['root_ou']}/{props['sandbox_ou']}",  # Sandbox OU
            ],
            resource_arns=arns,
        )
