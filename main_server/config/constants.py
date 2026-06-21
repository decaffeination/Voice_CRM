"""项目常量定义。"""

# Memory
HISTORY_ACTIVE_ROUNDS = 20
SUMMARY_TRIGGER_COUNT = 50

# JWT
TOKEN_TYPE = "bearer"

# 写库确认状态
PENDING_WRITE_DRAFT = "draft"
PENDING_WRITE_AWAITING = "awaiting_confirm"
PENDING_WRITE_CONFIRMED = "confirmed"
PENDING_WRITE_CANCELLED = "cancelled"

# 写库类型
WRITE_TYPE_CUSTOMER = "customer"
WRITE_TYPE_FOLLOWUP = "followup"
WRITE_TYPE_CONTRACT = "contract"
WRITE_TYPE_ORDER = "order"

# 写库动作（增/改/删均需人工确认后执行）
MUTATION_CREATE = "create"
MUTATION_UPDATE = "update"
MUTATION_DELETE = "delete"

WRITE_ACTIONS = frozenset({MUTATION_CREATE, MUTATION_UPDATE, MUTATION_DELETE})
WRITE_ENTITY_TYPES = frozenset(
    {WRITE_TYPE_CUSTOMER, WRITE_TYPE_FOLLOWUP, WRITE_TYPE_CONTRACT, WRITE_TYPE_ORDER}
)

ENTITY_ID_KEYS: dict[str, str] = {
    WRITE_TYPE_CUSTOMER: "customer_id",
    WRITE_TYPE_FOLLOWUP: "followup_id",
    WRITE_TYPE_ORDER: "order_id",
    WRITE_TYPE_CONTRACT: "contract_id",
}

# 默认分页
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# 数据库 dialect
DB_SQLITE = "sqlite"
DB_POSTGRESQL = "postgresql"
SUPPORTED_DB_DIALECTS = frozenset({DB_SQLITE, DB_POSTGRESQL})

# 技术栈
VECTOR_DB_CHROMA = "chromadb"
LLM_PROVIDER = "deepseek"
ASR_PROVIDER = "funasr"
VAD_PROVIDER = "silero-vad"
TTS_PROVIDER = "chattts"
EMBEDDING_MODEL = "BAAI/bge-small-zh-v1.5"
RERANK_MODEL = "BAAI/bge-reranker-base"

# Agent 多步工具
MAX_TOOL_STEPS = 6

# 本地模型目录（相对项目根目录）
MODELS_BASE_PATH = "main_server/data/models"
ASR_MODEL_DIR = "SenseVoiceSmall"
EMBEDDING_CACHE_DIR = "embedding"
RERANK_CACHE_DIR = "rerank"
VAD_MODEL_DIR = "silero_vad"
TTS_MODEL_DIR = "chattts"
