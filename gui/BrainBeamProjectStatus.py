import json
from rich.table import Table
from rich.console import Console
import pandas as pd
import os
import ipdb

class ProjectStatus():
    """ Project Status:
    Given a json file written as BrainBeam project file,
    This class will reshape relevant data into a Table for command line
    And then print said table.
    """
    def __init__(self,file):
        self.dir=file
        with open(self.dir) as fileob: 
            self.file=json.load(fileob)

    def __call__(self):
        self.strip_file()
        self.display_table()
    
    def strip_file(self):
        for i,(row, dict) in enumerate(self.file.items()):
            for attribute,value in dict.items():
                if value=='pending':
                    dict[attribute]=f'[blue]{value}[/blue]'
                elif value=='complete':
                    dict[attribute]=f'[green]{value}[/green]'
                elif value=='error':
                    dict[attribute]=f'[red]{value}[/red]'
                elif value=='running':
                    dict[attribute]=f'[yellow]{value}[/yellow]'
                else:
                    dict[attribute]=f'[magenta bold]{value}[/magenta bold]'
                #ipdb.set_trace()

            if i==0:
                dfT=pd.json_normalize(dict)
            else:
                dfoh=pd.json_normalize(dict)
                dfT=pd.concat([dfT, dfoh], ignore_index=True)
        self.dfT = dfT[dfT.columns.drop(list(dfT.filter(regex='path')))]

    def display_table(self):
        titlename=os.path.basename(self.dir)
        table=Table(title=f'Project: {titlename}')
        rows=self.dfT.values.tolist()
        rows = [[str(el) for el in row] for row in rows]
        columns = self.dfT.columns.tolist()
        
        for column in columns:
            table.add_column(column)

        for row in rows:
            table.add_row(*row, style='bright_green')
        
        console=Console()
        console.print(table)


if __name__=='__main__':
    exproj=r"C:\\Users\\listo\\test1.json"
    projoh = ProjectStatus(exproj)
    projoh()


