import tree_sitter_python
from tree_sitter import Language, Parser
lang = Language(tree_sitter_python.language())
parser = Parser(lang)
src = b'my_secret = os.getenv("sk_live_1234567890abcdef")'
tree = parser.parse(src)
print(tree.root_node)

src2 = b'config_key = os.environ["sk_live_1234567890abcdef"]'
tree2 = parser.parse(src2)
print(tree2.root_node)
