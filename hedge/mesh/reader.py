"""Mesh topology/geometry representation."""

from __future__ import division

__copyright__ = "Copyright (C) 2009 Xueyu Zhu, Andreas Kloeckner"

__license__ = """
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see U{http://www.gnu.org/licenses/}.
"""

import numpy
from pytools import memoize


# gmsh nodes-per-elements
@memoize
def _get_gmsh_element_type_to_info_map():
    from pytools import Record
    class ElementTypeInfo(Record):
        __slots__ = ['ele_type']
    from hedge.element import TriangularElement,TetrahedralElement
    return {
            2:  ElementTypeInfo(ele_type=TriangularElement(1)),
            4:  ElementTypeInfo(ele_type=TetrahedralElement(1)),
            9:  ElementTypeInfo(ele_type=TriangularElement(2)),
            11: ElementTypeInfo(ele_type=TetrahedralElement(2)), 
            20: ElementTypeInfo(ele_type=TriangularElement(3)),
            21: ElementTypeInfo(ele_type=TriangularElement(3)),
            22: ElementTypeInfo(ele_type=TriangularElement(4)),
            23: ElementTypeInfo(ele_type=TriangularElement(4)),
            24: ElementTypeInfo(ele_type=TriangularElement(5)),
            25: ElementTypeInfo(ele_type=TriangularElement(5)),
            29: ElementTypeInfo(ele_type=TetrahedralElement(3)),
            30: ElementTypeInfo(ele_type=TetrahedralElement(4)),
            31: ElementTypeInfo(ele_type=TetrahedralElement(5))
           }
   
def make_read_mesh(nodes,elements, elements_info, phy_tags,
            boundary_tagger=(lambda fvi, el, fn, all_v: [])):
    from hedge.mesh import make_conformal_mesh
    
    return make_conformal_mesh(
            nodes,
            elements,
            boundary_tagger)



def read_gmsh(filename):
    """
    mesh reader for gmsh file
    """
    from hedge.element import TriangularElement,TetrahedralElement
    # open target file
    mesh_file = open(filename, 'r')
    lines     = mesh_file.readlines()

    # get the element type map
    element_type_map = _get_gmsh_element_type_to_info_map()
    # collect the mesh information
    nodes            = []
    elements_2D      = []
    elements_3D      = []
    elements_info    = []
    phy_tags         = []
    i = 0
    while i < len(lines):
        l = lines[i].strip()
        i += 1  
        if l == "$MeshFormat":
            while True:
                i+=1
                l = lines[i].strip()
                if l == "$EndMeshFormat":
                    break 
            i+=1
        elif l == "$Nodes":
            l = lines[i].strip()
            Nv = numpy.int(l)
            while True:
                i +=1
                l = lines[i].strip()
                lvalue = l.split()
                if l == "$EndNodes":
                    break
                nodes.append([float(x) for x in lvalue[1:]])
            i+=1
        elif l == "$Elements":
            l = lines[i].strip()
            K = numpy.int(l)
            EToV = []
            while True:
                i +=1
                l = lines[i].strip() 
                if l == "$EndElements":
                    break
                l_str = l.split()    
                lvalue = [int(x) for x in l_str] 
                type = "unsupported"
                # store the element table for supported elements
                if lvalue[1] in element_type_map.keys():
                    type = element_type_map[lvalue[1]]
                    if isinstance(type.ele_type,TriangularElement):
                        elements_2D.append([x-1 for x in lvalue[3+lvalue[2]:]])
                    elif isinstance(type.ele_type,TetrahedralElement):
                        elements_3D.append([x-1 for x in lvalue[3+lvalue[2]:]])
                # store information for all kinds of elements
                elements_info.append(
                                     dict(
                                          ele_indices = lvalue[0],
                                          el_type     = type,
                                          ele_number_of_tags =lvalue[2],
                                          el_tags = lvalue[3:3+lvalue[2]],
                                          nodes   = lvalue[3+lvalue[2]:] 
                                         )
                                     )
            i+=1
        elif l == "$PhysicalNames":
            l = lines[i].strip()
            no_tags = numpy.int(l)
            phy_tags = []
            while True:
                i +=1
                l = lines[i].strip() 
                if l == "$EndPhysicalNames":
                    break
                l_str = l.split()    
                lvalue = [int(x) for x in l_str[:-1]] 
                phy_tags.append(
                                dict(
                                     phy_dimension = lvalue[0],
                                     tag_index = lvalue[1],
                                     tag_name  = l_str[-1].replace('\"',' ')
                                     )
                                )                                
            i+=1
        else: 
            # unrecognized section, skip 
            pass

    # initialize Mesh class,need to figure out the mapping 
    # for making higher order element
    # extracting computational elements for 2D/3D 
    elements = elements_2D
    points   = [ x[0:2] for x in nodes ]
    if elements_3D!=[]:
        elements = elements_3D
        points   = nodes

    input_mesh = make_read_mesh(points,elements,elements_info,phy_tags)   
    #close the file explicitly
    mesh_file.close
    return input_mesh





