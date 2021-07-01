from aws_cdk import core as cdk, aws_ec2 as ec2


class TestStack(cdk.Stack):
    def __init__(self, scope: cdk.Construct, id: str, vpc=ec2.IVpc, **kwargs) -> None:
        super().__init__(scope=scope, id=id, **kwargs)

        sg_ssh = ec2.SecurityGroup(
            self, "sg_allow_ssh", vpc=vpc, allow_all_outbound=True
        )

        sg_ssh.add_ingress_rule(
            ec2.Peer.ipv4("10.0.0.0/8"),
            ec2.Port.tcp(22),
            "Allow SSH connection from internal network",
        )

        self.ec2_instance = ec2.Instance(
            self,
            "test-instance",
            instance_type=ec2.InstanceType("t2.micro"),
            machine_image=ec2.AmazonLinuxImage(generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2),
            vpc=vpc,
            key_name="networking-keypair",
            security_group=sg_ssh,
            vpc_subnets=ec2.SubnetSelection(subnet_group_name="infrastructure"),
        )
