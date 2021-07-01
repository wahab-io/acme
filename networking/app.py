import os

from aws_cdk import core

from networking.networking_stack import NetworkingStack
from networking.vpn_stack import VpnStack
from test_stack import TestStack

from dotenv import load_dotenv

load_dotenv()

networking_props = {
    "management_account": os.getenv("MANAGEMENT_ACCOUNT"),
    "root_ou": os.getenv("ROOT_OU"),
    "non_production_ou": os.getenv("NON_PRODUCTION_OU"),
    "sandbox_ou": os.getenv("SANDBOX_OU")
}


app = core.App()
networking = NetworkingStack(app, "networking", networking_props)
vpn = VpnStack(app, "vpn", networking.vpc)
test = TestStack(app, "test", networking.vpc)

app.synth()
