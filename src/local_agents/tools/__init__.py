from local_agents.tools.analyze import CompareDocsTool, MultiHopSearchTool, SummarizeDocTool
from local_agents.tools.docs import DocSearchTool, ListDocsTool, ReadDocTool
from local_agents.tools.misc import CalcTool, NowTool

TOOL_REGISTRY = {
    "list_docs": ListDocsTool,
    "read_doc": ReadDocTool,
    "search_docs": DocSearchTool,
    "summarize_doc": SummarizeDocTool,
    "compare_docs": CompareDocsTool,
    "multihop_search": MultiHopSearchTool,
    "calc": CalcTool,
    "now": NowTool,
}
