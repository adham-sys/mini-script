from dataclasses import dataclass,field 
from typing import Dict,List ,Optional,Union
import re
from enum import Enum
   
class Tag(Enum):
    self_close = 0 
    fragment   = 1

@dataclass
class Node:
    id:int
    designp:Tag|None
    type:str
    attributes: dict|None = field(default_factory=dict)
@dataclass
class SVGParse:
    node: Node | None = None
    children: List[Union['SVGParse', 'Node']] = field(default_factory=list)
def cleanTAg(TAG):
    if TAG.startswith("/"):
        return TAG[1:].rstrip(">")
    return TAG.rstrip(">")
stack = [SVGParse()]

with open("blender.svg","r") as f:
    tokens = f.readlines()  
    id = 0
    for token in tokens:
        attr:dict = {}
        parts = token.split()

        if not parts:
          continue

        T = parts[0]

        if T:
            pattern = r'([\w:-]+)="([^"]*)"'
            for key, value in re.findall(pattern, token):
                attr[key] = value.strip()
            match token:
                case _ if re.fullmatch(r" +<!--.*?-->\n",token):
                    continue
                case _ if T.startswith("</"):
                    if len(stack) > 1:
                        stack.pop()              
                case _ if token.strip().endswith("/>"):
                     TOK = cleanTAg(T[1:])
                     stack[-1].children.append(Node(id,Tag.self_close,TOK,attr))
                     id += 1
                                  
                case _ if token.strip().endswith(">"):
                    TOK = cleanTAg(T[1:])
                    if stack[-1].node is None:
                        stack[-1].node = Node(id,Tag.fragment,TOK,attr)
                        id += 1 
                    else:
                        new_node = SVGParse(Node(id,Tag.fragment, TOK, attr))
                        stack[-1].children.append(new_node)
                        stack.append(new_node) 
                        id += 1 
                # case _:
                #     TOK = cleanTAg()
                #     root.children.append(Node(id,tag.fragment.value,TOK,attr))
                #     id += 1  
def print_tree(tree, depth=0):
    indent = "    " * depth

    if tree.node is not None:
        print(f"{indent}{tree.node.type} (id={tree.node.id})")

    for child in tree.children:
        if isinstance(child, Node):
            print(f"{indent}  {child.type} (id={child.id}) [self-close]")
        else:
            print_tree(child, depth + 1)
print_tree(stack[0])            
              


