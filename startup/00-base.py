import os
import nslsii
import time

from bluesky import RunEngine
from bluesky.callbacks.buffer import BufferingWrapper
from bluesky_tiled_plugins import TiledInserter
from redis_json_dict import RedisJSONDict
from tiled.client import from_profile
from ophyd.signal import EpicsSignalBase
from databroker import Broker

EpicsSignalBase.set_defaults(timeout=60, connection_timeout=60)  # new style

from IPython import get_ipython
from IPython.terminal.prompts import Prompts, Token

# Configure a Tiled writing client
tiled_writing_client_raw = from_profile("nsls2", api_key=os.environ["TILED_BLUESKY_WRITING_API_KEY_CHX"])["chx"]["raw"]
tiled_writing_client_raw.context.http_client.headers['tiled-qos'] = 'acquisition'
TILED_BACKUP_ROOT = "/nsls2/data/chx/shared/config/bluesky/tiled_backup"

tiled_inserter = TiledInserter(
    tiled_writing_client_raw,
    "chx",
    backup_directory=f"{TILED_BACKUP_ROOT}/raw",
)
tiled_inserter = BufferingWrapper(tiled_inserter)  # in-process queue: RE never blocks

nslsii.configure_base(get_ipython().user_ns,
                      tiled_inserter,
                      redis_url="xf11id1-chx-redis1.nsls2.bnl.gov",
                      redis_port=6380,
                      redis_ssl=True,
                      publish_documents_with_kafka="chx")

print("Initializing Tiled reading client...\nMake sure you check for duo push.")
tiled_reading_client = from_profile("nsls2", username=None, include_data_sources=True)["chx"]["raw"]
tiled_reading_client.context.http_client.headers['tiled-qos'] = 'acquisition'

db = Broker(tiled_reading_client)

# set plot properties for 4k monitors
plt.rcParams["figure.dpi"] = 200


# Setup the path to the secure assets folder for the current proposal
def assets_path():
    return f"/nsls2/data/chx/proposals/{RE.md['cycle']}/{RE.md['data_session']}/assets/"


class ProposalIDPrompt(Prompts):
    def in_prompt_tokens(self, cli=None):
        return [
            (
                Token.Prompt,
                f"{RE.md.get('data_session', 'N/A')} [",
            ),
            (Token.PromptNum, str(self.shell.execution_count)),
            (Token.Prompt, "]: "),
        ]


ip = get_ipython()
ip.prompts = ProposalIDPrompt(ip)
