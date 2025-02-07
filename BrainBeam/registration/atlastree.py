#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module Name: dataframes.py
Description: From registration output, convert data into a tall formatted dataframe  
Author: David Estrin
Date: 2024-008-15
Version: 2.0
Usage: python DataMerger.py --input data.csv --output results.csv
"""
import os
import json
import ipdb
import tqdm

class atlastree:
    def __init__(self, data):
        self.data = data
        self.tree = {}
        self.id_to_node = {}
        self.name_to_id = {}
        self.build_tree()

    def build_tree(self):
        """Builds a hierarchical tree from the given structure data."""
        for entry in self.data:
            entry = self.data[entry]
            structure_id = entry["id"]
            structure_name = entry["name"]
            structure_id_path = entry["structure_id_path"]
            
            # Store node info
            self.id_to_node[structure_id] = {
                "id": structure_id,
                "name": structure_name,
                "parent": None if len(structure_id_path) == 1 else structure_id_path[-2],
                "level": len(structure_id_path),
                "children": []
            }
            self.name_to_id[structure_name.lower()] = structure_id  # Case-insensitive name lookup

        # Establish parent-child relationships
        for node in self.id_to_node.values():
            parent_id = node["parent"]
            if parent_id in self.id_to_node:
                self.id_to_node[parent_id]["children"].append(node["id"])

    def find_node(self, id_or_name):
        """Find a node by ID or name."""
        if isinstance(id_or_name, int):  # Look up by ID
            return self.id_to_node.get(id_or_name)
        elif isinstance(id_or_name, str):  # Look up by name
            node_id = self.name_to_id.get(id_or_name.lower())
            return self.id_to_node.get(node_id)
        return None

    def get_parents(self, id_or_name):
        """Returns a list of all parent structures (from direct parent to root)."""
        node = self.find_node(id_or_name)
        if not node:
            if id_or_name not in str(self.data):
                print('This ID is not part of data. Check spelling or something....')
                return []
            else:
                return []
        
        parents = []
        current_id = node["parent"]
        while current_id:
            parent_node = self.id_to_node.get(current_id)
            if not parent_node:
                break
            parents.append(parent_node["name"])
            current_id = parent_node["parent"]
        return parents[::-1]  # Return from root to direct parent

    def get_children(self, id_or_name):
        """Returns a list of all direct child structures."""
        node = self.find_node(id_or_name)
        if not node:
            if id_or_name not in str(self.data):
                print('This ID is not part of data. Check spelling or something....')
                return []
            else:
                return []
        return [self.id_to_node[child_id]["name"] for child_id in node["children"]]

    def print_tree(self, node_id=None, level=0):
        """Recursively prints the tree structure."""
        if node_id is None:
            root_nodes = [n for n in self.id_to_node.values() if n["parent"] is None]
            for root in root_nodes:
                self.print_tree(root["id"], 0)
            return

        node = self.id_to_node[node_id]
        print("  " * level + f"- {node['name']} (ID: {node['id']})")
        for child_id in node["children"]:
            self.print_tree(child_id, level + 1)

    def level_helper(self,node_name,level):
        """ Get regions at specific level of brain """
        children = self.get_children(node_name)
        
        regions_at_level = []
        if children:
            for region_name in children:
                node_oh = self.find_node(region_name)
                
                if node_oh["level"] == level:
                    regions_at_level.append(region_name)

                elif node_oh["level"] < level:
                    regions_at_level.append(self.level_helper(node_name=region_name,level=level))
                
                elif node_oh["level"] > level:
                    regions_at_level.append(self.level_helper(node_name=self.get_parents(id_or_name = region_name)[-1],level=level))
        
        #remove lists of lists to single list
        regions_at_level = self.flatten_list(nested_list=regions_at_level)

        return list(set(regions_at_level))

    def flatten_list(self, nested_list):
        """Recursively flattens a list with unknown depth."""
        flattened = []
        for item in nested_list:
            if isinstance(item, list):
                flattened.extend(self.flatten_list(item))  # Recursively flatten
            else:
                flattened.append(item)
        
        return flattened

    def leveler(self,level_oh):
        result = []
        for entry in tqdm.tqdm(self.data.values()):
            result.append(self.level_helper(node_name=entry["name"],level=level_oh))
        result = self.flatten_list(nested_list=result)
        return list(set(result))  # Remove duplicates

# Example Usage
if __name__ == "__main__":
    data_path = r'C:\Users\listo\example_registration_data\test_registration_communal_drop' 
    drop_atlas_path = os.path.join(data_path,"communal_atlas_drop/")

    # Open structures atlas file
    atlas_json_file = os.path.join(drop_atlas_path,'structures.json')
    with open(atlas_json_file,'r') as infile:
        ontology_dict = json.load(infile)

    # Convert list to dictonary 
    ontology_dict_oh = {i: v for i, v in enumerate(ontology_dict)}

    # Build tree
    tree = atlastree(data = ontology_dict_oh)
    tree.get_children("dave")


