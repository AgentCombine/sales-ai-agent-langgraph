HOST = "::1"
PORT = 8501
LLM_MODEL = "unsloth/Qwen3-Next-Instruct"
LLM_BASE_URL = "http://localhost:8001/v1"
LLM_API_KEY = ""
CUSTOMER_ID = None
THREAD_ID = None


def configure(args) -> None:
    g = globals()
    for k, v in vars(args).items():
        name = k.upper().replace("-", "_")
        if name in g:
            g[name] = v
