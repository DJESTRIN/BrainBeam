""" BrainBeamBase
The purpose of this script is to set up the basic classes and subsquent GUIs to run BrainBeam
"""
import tkinter as tk
import customtkinter as ctk
import os, glob
import threading
from PIL import Image
from tkinter import filedialog
import json

from BrainBeamCLI import API, PipelineError

ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"
ctk.set_appearance_mode("System")

# Shared style constants for a consistent, professional look across all tabs.
FONT_TITLE = ("Segoe UI", 22, "bold")
FONT_SECTION = ("Segoe UI", 16, "bold")
FONT_BODY = ("Segoe UI", 13)
FONT_BUTTON = ("Segoe UI", 13, "bold")
FONT_STATUS = ("Segoe UI", 12)
COLOR_SUCCESS = "#2FA84F"
COLOR_ERROR = "#D64545"
COLOR_RUNNING = "#E0972F"
COLOR_MUTED = "gray55"
SECONDARY_BUTTON = {"fg_color": "gray35", "hover_color": "gray25"}

class BrainBeamGuiBase():
    def __init__(self):
        self.root=ctk.CTk()
        self.root.title("BrainBeam Pipeline Manager")
        self._set_initial_geometry()
        self.root.minsize(1000, 650)
        gui_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(gui_dir, "images", "brain.ico")
        if os.path.exists(icon_path) and os.path.getsize(icon_path) > 0:
            try:
                self.root.iconbitmap(icon_path)
            except tk.TclError:
                pass
        self.wd=os.getcwd()
        self.index=0
        #self.root.overrideredirect(True)
        #self.close_button = ctk.CTkButton(self.root, text='Quit', width=1, font=('Arial bold',15), command=self.root.destroy).place(relx=0.95,rely=0.03,anchor=CENTER)

        #Side Bar
        self.sidebar_frame = ctk.CTkFrame(self.root, width=180, height=1000, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)
        self.sidebar_title = ctk.CTkLabel(self.sidebar_frame, text="BrainBeam", font=FONT_TITLE)
        self.sidebar_title.place(relx=0.5, rely=0.12, anchor='n')
        #self.copybutton=ctk.CTkButton(master=self.sidebar_frame,text="Start by Adding \n Lightsheet Data", width = 20,font=('Arial',15,'bold'),command=self.copydata).place(relx=0.85,rely=0.25,anchor='e')
    
        #Set up radio buttons
        self.set_up_radio_buttons()
        
        # Set up Tab page
        self.tabview = ctk.CTkTabview(self.root, width=self.tab_width,height=self.tab_height)
        self.tabview.place(relx=0.57, rely=0.49, anchor=tk.CENTER)
        self.tabview.add("Overview")
        self.tabview.add("Copy, Move & Compress")
        self.tabview.add("Denoise")
        self.tabview.add("Stitch")
        self.tabview.add("Registration")
        self.tabview.add("Segmentation")
        self.tabview.add("Custom Script")
        self.tabview.tab("Overview").grid_columnconfigure(0, weight=1)  # configure grid of individual tabs

        self.set_up_custom_script()
        self.call_logo()
        self.set_up_overview()
        self.set_up_copy()
        self.set_up_denoise()
        self.set_up_stitch()
        self.set_up_registration()
        self.set_up_segmentation()

    def _set_initial_geometry(self):
        #Size the window to fit comfortably on the current screen (falls back to a
        #sensible default on very small displays) instead of always opening at a fixed
        #1250x900, which could be too large for laptop screens or off-center on others.
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        width = min(1250, int(screen_w * 0.9))
        height = min(900, int(screen_h * 0.9))
        x = max(0, (screen_w - width) // 2)
        y = max(0, (screen_h - height) // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        # Reserve room for the sidebar so the tabview itself scales with the window
        # instead of always requesting a fixed 1000x800, which would clip on smaller screens.
        self.tab_width = max(700, width - 220)
        self.tab_height = max(500, height - 80)

    def get_project_file_path(self):
        if self.projectfiledir.endswith('.json'):
            return self.projectfiledir
        return f'{self.projectfiledir}.json'

    def set_up_overview(self):
        #Set log image
        self.webbtn = ctk.CTkButton(self.tabview.tab("Overview"),text="Create Project",font=FONT_BUTTON,command=self.set_up_project)
        self.webbtn.place(relx=0.01,rely=0.01)
        self.webbtn = ctk.CTkButton(self.tabview.tab("Overview"),text="Open Project",font=FONT_BUTTON,command=self.open_project)
        self.webbtn.place(relx=0.17,rely=0.01)
        self.webbtn = ctk.CTkButton(self.tabview.tab("Overview"),text="Import New Data to Project",font=FONT_BUTTON,command=self.AddNewData)
        self.webbtn.place(relx=0.33,rely=0.01)

    def open_project(self):
        # Open a Brain Beam JSON project file
        self.projectfiledir=filedialog.askopenfilename(initialdir=self.wd,filetypes =[('json', '*.json')])
        with open(self.projectfiledir, 'r') as openfile:
            self.overviewdict = json.load(openfile)
            self.index=len(self.overviewdict)

        self.updateoverview()

    def AddNewData(self):
        # Add New data to a currently opened project
        try: #Open new directory with new data
            if len(self.overviewdict)>0:
                directory=self.select_folder('Please select folder containing NEW lightsheet data! Note, please see our wiki regarding data formating')
                self.add_folders_to_dict(directory)
                self.updateoverview() 

        except AttributeError:
            self.throw_error('Please open or create a project before adding new data')

    def set_up_project(self):
        #Get Project file info from user
        self.projectfiledir=filedialog.asksaveasfilename(title="Please save Project File",initialdir=self.wd,filetypes =[('json', '.json')])

        #Open folder containing the new data
        directory=self.select_folder('Please select folder containing lightsheet data! Note, please see our wiki regarding dataformating') # get the directory
        self.add_folders_to_dict(directory)
        self.updateoverview()
    
    def add_folders_to_dict(self,directory):
        if self.index==0:
            self.overviewdict={}
        if os.path.exists(os.path.join(directory,'lightsheet')): # If it is a folder containing samples
            # Search for samples in folder
            datapath=os.path.join(directory,"lightsheet")
            datapath=os.path.join(datapath,"raw") +'/*'
            self.samples=glob.glob(datapath)

            #Loop through folder and add new sample data
            for i,sample in enumerate(self.samples):
                samplename=os.path.basename(sample)
                foldername = os.path.basename(directory)    # Get directory name
                dict_oh={'parentfoldername':foldername,'samplename':samplename,'Imported':'complete','Copied':'pending', 'Moved':'pending','Compressed':'pending','Converted':'pending',
                         'Denoise':'pending','Stitch':'pending','Registration':'pending','Segmentation':'pending','Custom Script':'pending','rawpath':sample}
                self.overviewdict[self.index]=dict_oh
                self.index+=1
        elif 'ex' in os.path.basename(directory).lower(): #When selecting a simple folder for with one sample
            samplename=os.path.basename(directory)
            foldername=None
            dict_oh={'parentfoldername':foldername,'samplename':samplename,'Imported':'complete','Copied':'pending', 'Moved':'pending','Compressed':'pending','Converted':'pending',
                         'Denoise':'pending','Stitch':'pending','Registration':'pending','Segmentation':'pending','Custom Script':'pending','rawpath':directory}
            self.overviewdict[self.index]=dict_oh
            self.index+=1
        else: #Input folder does not fit our format
            self.throw_error('The selected folder does \n not fit our format :( \n Select a new folder or reformat current folder \n please see our wiki on github.com')
        
        # Save json dictionary for project to a file. 
        try:
            #Write json into a file
            self.overviewdict=json.dumps(self.overviewdict,indent=4)
            with open(self.get_project_file_path(), "w") as outfile:
                outfile.write(self.overviewdict)
            
            with open(self.get_project_file_path(), 'r') as openfile:
                self.overviewdict = json.load(openfile)
        except AttributeError:
            self.throw_error('The Project file was not created')
        
    def updateoverview(self):
        self.set_up_overview_headers()

        # Destroy previously made images if any
        try:
            for label in self.all_overview_images:
                label.destroy() 
        except AttributeError:
            self.all_overview_images=[]

        # Load status icons (falls back to colored text symbols if an icon asset is missing,
        # so the overview table never crashes even if images are unavailable).
        gui_dir = os.path.dirname(os.path.abspath(__file__))
        icon_files={'pending':'pending.png','complete':'complete.png','error':'error.png','running':'running.png'}
        status_icons={}
        for status,filename in icon_files.items():
            icon_path=os.path.join(gui_dir,"images",filename)
            status_icons[status]=ctk.CTkImage(Image.open(icon_path),size=(20,20)) if os.path.exists(icon_path) else None
        nextstep_path=os.path.join(gui_dir,"images","nextstep.png")
        nextstep_icon=ctk.CTkImage(Image.open(nextstep_path),size=(15,7)) if os.path.exists(nextstep_path) else None
        status_symbols={'pending':('\u25cb',COLOR_MUTED),'complete':('\u2714',COLOR_SUCCESS),'error':('\u2716',COLOR_ERROR),'running':('\u25f4',COLOR_RUNNING)}

        row_oh=1
        for sample in self.overviewdict:
            dict_oh=self.overviewdict[sample]
            for key,value in dict_oh.items():
                #Determine display icon (or fallback symbol/color) for this status value
                icon=status_icons.get(value)
                symbol,color=status_symbols.get(value,('?',COLOR_MUTED))

                def make_status_label(icon=icon,symbol=symbol,color=color):
                    if icon is not None:
                        return ctk.CTkLabel(self.overview_frame, text="", height=10, width=10, image=icon)
                    return ctk.CTkLabel(self.overview_frame, text=symbol, text_color=color, height=10, width=10)

                #generate status label
                label=None
                if key=='samplename':
                    label=ctk.CTkLabel(self.overview_frame, text=value, font=('Arial',10,'bold'))
                    label.grid(row=row_oh,column=1)
                if key=='Imported':
                    label=make_status_label(); label.grid(row=row_oh,column=3)
                if key=='Copied':
                    label=make_status_label(); label.grid(row=row_oh,column=5)
                if key=='Moved':
                    label=make_status_label(); label.grid(row=row_oh,column=7)
                if key=='Compressed':
                    label=make_status_label(); label.grid(row=row_oh,column=9)
                if key=='Converted':
                    label=make_status_label(); label.grid(row=row_oh,column=11)
                if key=='Denoise':
                    label=make_status_label(); label.grid(row=row_oh,column=13)
                if key=='Stitch':
                    label=make_status_label(); label.grid(row=row_oh,column=15)
                if key=='Registration':
                    label=make_status_label(); label.grid(row=row_oh,column=17)
                if key=='Segmentation':
                    label=make_status_label(); label.grid(row=row_oh,column=19)
                if key=='Custom Script':
                    label=make_status_label(); label.grid(row=row_oh,column=21)

                #Put labels in a common list
                if label is not None:
                    self.all_overview_images.append(label)
            row_oh+=1

        for row_oh in range(len(self.overviewdict)):
            for i in range(21):
                if ( i % 2 ) == 0: 
                    if i==0 or i==2:
                        continue
                    if nextstep_icon is not None:
                        arrow_label = ctk.CTkLabel(self.overview_frame, text="", height=10, width=10, image=nextstep_icon)
                    else:
                        arrow_label = ctk.CTkLabel(self.overview_frame, text="\u2192", height=10, width=10)
                    arrow_label.grid(row=row_oh+1,column=i)


    def set_up_overview_headers(self):
        if hasattr(self, 'overview_frame'):
            self.overview_frame.destroy()
        self.overview_frame = ctk.CTkFrame(self.tabview.tab("Overview"), corner_radius=0,width=350,height=500)
        self.overview_frame.place(relx=0.01, rely=0.05)
        self.overview_frame.grid_rowconfigure(len(self.overviewdict)+2, weight=1)
        self.overview_frame.grid_columnconfigure(21, weight=1)
        self.samplelabel=ctk.CTkLabel( self.overview_frame,text="Imported",font=('Arial',12,'bold')).grid(row=0, column=3, padx=5, pady=5)
        self.samplelabel=ctk.CTkLabel( self.overview_frame,text="Copied",font=('Arial',12,'bold')).grid(row=0, column=5, padx=5, pady=5)
        self.samplelabel=ctk.CTkLabel( self.overview_frame,text="Moved",font=('Arial',12,'bold')).grid(row=0, column=7, padx=5, pady=5)
        self.samplelabel=ctk.CTkLabel( self.overview_frame,text="Compressed",font=('Arial',12,'bold')).grid(row=0, column=9, padx=5, pady=5)
        self.samplelabel=ctk.CTkLabel( self.overview_frame,text="Converted",font=('Arial',12,'bold')).grid(row=0, column=11, padx=5, pady=5)
        self.samplelabel=ctk.CTkLabel( self.overview_frame,text="Denoised",font=('Arial',12,'bold')).grid(row=0, column=13, padx=5, pady=5)
        self.samplelabel=ctk.CTkLabel( self.overview_frame,text="Stitched",font=('Arial',12,'bold')).grid(row=0, column=15, padx=5, pady=5)
        self.samplelabel=ctk.CTkLabel( self.overview_frame,text="Registered",font=('Arial',12,'bold')).grid(row=0, column=17, padx=5, pady=5)
        self.samplelabel=ctk.CTkLabel( self.overview_frame,text="Segmented",font=('Arial',12,'bold')).grid(row=0, column=19, padx=5, pady=5)
        self.samplelabel=ctk.CTkLabel( self.overview_frame,text="Custom",font=('Arial',12,'bold')).grid(row=0, column=21, padx=5, pady=5)

    def select_folder(self,label='Open Folder'):
        return filedialog.askdirectory(title=label,initialdir=self.wd)

    def select_folder_into_entry(self,entry,label='Open Folder'):
        folder=self.select_folder(label=label)
        if folder:
            entry.delete(0,tk.END)
            entry.insert(0,folder)
        return folder

    def throw_error(self,message):
        self.error=ctk.CTk()
        self.error.geometry("500x100")
        self.errmessage=ctk.CTkLabel(self.error,text=message).pack()
        self.error.mainloop()

    def get_computertype(self):
        #Radio button values: 0=Local, 1=SLURM HPC, 2=AWS
        mapping={'0':'local','1':'slurm','2':'aws'}
        return mapping.get(str(self.radio_var.get()),'local')

    ACTION_TO_OVERVIEW_KEY={'Copy':'Copied','Move':'Moved','Compress':'Compressed','Denoise':'Denoise',
                            'Stitch':'Stitch','Register':'Registration','Segment':'Segmentation','Custom':'Custom Script'}

    def update_sample_status(self,target_path,action_name,status):
        #Best-effort sync of a sample's stage status in the overview table/project file.
        #Matches samples whose stored rawpath is a prefix/substring of the given target_path.
        overview_key=self.ACTION_TO_OVERVIEW_KEY.get(action_name)
        if not overview_key or not target_path or not hasattr(self,'overviewdict') or not self.overviewdict:
            return
        target_path=os.path.normpath(target_path)
        changed=False
        for dict_oh in self.overviewdict.values():
            rawpath=dict_oh.get('rawpath')
            if rawpath and (os.path.normpath(rawpath) in target_path or target_path in os.path.normpath(rawpath)):
                dict_oh[overview_key]=status
                changed=True
        if not changed:
            return
        try:
            with open(self.get_project_file_path(),'w') as outfile:
                json.dump(self.overviewdict,outfile,indent=4)
        except AttributeError:
            pass
        self.updateoverview()

    def run_backend_action(self,status_label,action_name,action,target_path=None):
        #Runs a BrainBeamCLI.API call on a background thread so the GUI does not freeze,
        #then marshals the status label update and overview sync back onto the Tkinter main thread.
        def update_label(text,color):
            self.root.after(0,lambda: status_label.configure(text=text,text_color=color))
        def sync_status(status):
            if target_path:
                self.root.after(0,lambda: self.update_sample_status(target_path,action_name,status))
        def worker():
            update_label(f"{action_name}: running...",COLOR_RUNNING)
            sync_status('running')
            try:
                api=API(self.get_computertype())
                action(api)
                update_label(f"{action_name}: complete.",COLOR_SUCCESS)
                sync_status('complete')
            except (PipelineError, NotImplementedError, ValueError, FileNotFoundError) as e:
                update_label(f"{action_name} failed: {e}",COLOR_ERROR)
                sync_status('error')
        threading.Thread(target=worker,daemon=True).start()

    def set_up_copy(self):
        #Set up the copy/move/compress tab
        #Description
        self.textbox2 = ctk.CTkTextbox(self.tabview.tab("Copy, Move & Compress"), width=1000,height=50)
        self.textbox2.insert("0.0", "The following are basic copy, move and compress functions. However, in BrainBeam, we have attempted to "+
                            "Maximize the speed of copying by moving folders in parallel. \nThese functions are most effecient when running on " +
                            "A SLURM based HPC.")
        self.textbox2.place(relx=0.0005,rely=0.01)

        #Copy Data
        self.copy_input_entry = ctk.CTkEntry(self.tabview.tab("Copy, Move & Compress"), width=600, placeholder_text="Input folder containing data that will be copied.")
        self.copy_input_entry.place(relx=0.01,rely=0.15)
        self.copy_output_entry = ctk.CTkEntry(self.tabview.tab("Copy, Move & Compress"), width=600, placeholder_text="Output folder where Input folder's data will be copied to.")
        self.copy_output_entry.place(relx=0.01,rely=0.2)
        self.labelcpy=ctk.CTkLabel(self.tabview.tab("Copy, Move & Compress"),text="Copy Data to Another Folder",font=FONT_SECTION,text_color=("gray10","gray90")).place(relx=0.01,rely=0.11)
        self.webbtn = ctk.CTkButton(self.tabview.tab("Copy, Move & Compress"),text="Find Input Folder",font=FONT_BUTTON,fg_color=SECONDARY_BUTTON["fg_color"],hover_color=SECONDARY_BUTTON["hover_color"],command=lambda: self.select_folder_into_entry(self.copy_input_entry,'Select folder to copy'))
        self.webbtn.place(relx=0.65,rely=0.15)
        self.webbtn = ctk.CTkButton(self.tabview.tab("Copy, Move & Compress"),text="Find Output Folder",font=FONT_BUTTON,fg_color=SECONDARY_BUTTON["fg_color"],hover_color=SECONDARY_BUTTON["hover_color"],command=lambda: self.select_folder_into_entry(self.copy_output_entry,'Select destination folder'))
        self.webbtn.place(relx=0.65,rely=0.2)
        self.webbtn = ctk.CTkButton(self.tabview.tab("Copy, Move & Compress"),text="Start Copying",font=FONT_BUTTON,command=self.start_copy)
        self.webbtn.place(relx=0.82,rely=0.15)
        self.copy_status_label = ctk.CTkLabel(self.tabview.tab("Copy, Move & Compress"),text="",font=FONT_STATUS)
        self.copy_status_label.place(relx=0.01,rely=0.24)

        #Move Data
        self.move_input_entry = ctk.CTkEntry(self.tabview.tab("Copy, Move & Compress"), width=600, placeholder_text="Input folder containing data that will be Moved.")
        self.move_input_entry.place(relx=0.01,rely=0.3)
        self.move_output_entry = ctk.CTkEntry(self.tabview.tab("Copy, Move & Compress"), width=600, placeholder_text="Output folder where Input folder's data will be Moved to.")
        self.move_output_entry.place(relx=0.01,rely=0.35)
        self.labelcpy=ctk.CTkLabel(self.tabview.tab("Copy, Move & Compress"),text="Move Data to Another Folder",font=FONT_SECTION,text_color=("gray10","gray90")).place(relx=0.01,rely=0.26)
        self.webbtn = ctk.CTkButton(self.tabview.tab("Copy, Move & Compress"),text="Find Input Folder",font=FONT_BUTTON,fg_color=SECONDARY_BUTTON["fg_color"],hover_color=SECONDARY_BUTTON["hover_color"],command=lambda: self.select_folder_into_entry(self.move_input_entry,'Select folder to move'))
        self.webbtn.place(relx=0.65,rely=0.3)
        self.webbtn = ctk.CTkButton(self.tabview.tab("Copy, Move & Compress"),text="Find Output Folder",font=FONT_BUTTON,fg_color=SECONDARY_BUTTON["fg_color"],hover_color=SECONDARY_BUTTON["hover_color"],command=lambda: self.select_folder_into_entry(self.move_output_entry,'Select destination folder'))
        self.webbtn.place(relx=0.65,rely=0.35)
        self.webbtn = ctk.CTkButton(self.tabview.tab("Copy, Move & Compress"),text="Start Moving",font=FONT_BUTTON,command=self.start_move)
        self.webbtn.place(relx=0.82,rely=0.3)
        self.move_status_label = ctk.CTkLabel(self.tabview.tab("Copy, Move & Compress"),text="",font=FONT_STATUS)
        self.move_status_label.place(relx=0.01,rely=0.39)

        #compress data
        self.compress_input_entry = ctk.CTkEntry(self.tabview.tab("Copy, Move & Compress"), width=600, placeholder_text="Input folder containing data that will be Compressed.")
        self.compress_input_entry.place(relx=0.01,rely=0.45)
        self.labelcpy=ctk.CTkLabel(self.tabview.tab("Copy, Move & Compress"),text="Compress Folder to tar.gz format",font=FONT_SECTION,text_color=("gray10","gray90")).place(relx=0.01,rely=0.41)
        self.webbtn = ctk.CTkButton(self.tabview.tab("Copy, Move & Compress"),text="Find Input Folder",font=FONT_BUTTON,fg_color=SECONDARY_BUTTON["fg_color"],hover_color=SECONDARY_BUTTON["hover_color"],command=lambda: self.select_folder_into_entry(self.compress_input_entry,'Select folder to compress'))
        self.webbtn.place(relx=0.65,rely=0.45)
        self.webbtn = ctk.CTkButton(self.tabview.tab("Copy, Move & Compress"),text="Start Compressing",font=FONT_BUTTON,command=self.start_compress)
        self.webbtn.place(relx=0.82,rely=0.45)
        self.compress_status_label = ctk.CTkLabel(self.tabview.tab("Copy, Move & Compress"),text="",font=FONT_STATUS)
        self.compress_status_label.place(relx=0.01,rely=0.49)

        #Decompress data
        self.decompress_input_entry = ctk.CTkEntry(self.tabview.tab("Copy, Move & Compress"), width=600, placeholder_text="Input folder containing .tar.gz archives which will be Decompressed")
        self.decompress_input_entry.place(relx=0.01,rely=0.55)
        self.labelcpy=ctk.CTkLabel(self.tabview.tab("Copy, Move & Compress"),text="Decompress tar.gz archives",font=FONT_SECTION,text_color=("gray10","gray90")).place(relx=0.01,rely=0.51)
        self.webbtn = ctk.CTkButton(self.tabview.tab("Copy, Move & Compress"),text="Find Input Folder",font=FONT_BUTTON,fg_color=SECONDARY_BUTTON["fg_color"],hover_color=SECONDARY_BUTTON["hover_color"],command=lambda: self.select_folder_into_entry(self.decompress_input_entry,'Select folder containing .tar.gz archives'))
        self.webbtn.place(relx=0.65,rely=0.55)
        self.webbtn = ctk.CTkButton(self.tabview.tab("Copy, Move & Compress"),text="Start Decompressing",font=FONT_BUTTON,command=self.start_decompress)
        self.webbtn.place(relx=0.82,rely=0.55)
        self.decompress_status_label = ctk.CTkLabel(self.tabview.tab("Copy, Move & Compress"),text="",font=FONT_STATUS)
        self.decompress_status_label.place(relx=0.01,rely=0.59)

        #Check processes
        self.webbtn = ctk.CTkButton(self.tabview.tab("Copy, Move & Compress"),text="Check status of code",font=FONT_BUTTON,command=self.select_folder,state=tk.DISABLED)
        self.webbtn.place(relx=0.4,rely=0.75)

    def start_copy(self):
        input_dir=self.copy_input_entry.get().strip()
        output_dir=self.copy_output_entry.get().strip()
        if not input_dir or not output_dir:
            self.throw_error('Please select both an input and output folder before copying.')
            return
        self.run_backend_action(self.copy_status_label,'Copy',lambda api: api.copy(input_dir,output_dir),target_path=input_dir)

    def start_move(self):
        input_dir=self.move_input_entry.get().strip()
        output_dir=self.move_output_entry.get().strip()
        if not input_dir or not output_dir:
            self.throw_error('Please select both an input and output folder before moving.')
            return
        self.run_backend_action(self.move_status_label,'Move',lambda api: api.move(input_dir,output_dir),target_path=input_dir)

    def start_compress(self):
        input_dir=self.compress_input_entry.get().strip()
        if not input_dir:
            self.throw_error('Please select a folder to compress.')
            return
        self.run_backend_action(self.compress_status_label,'Compress',lambda api: api.compress(input_dir),target_path=input_dir)

    def start_decompress(self):
        input_dir=self.decompress_input_entry.get().strip()
        if not input_dir:
            self.throw_error('Please select a folder containing .tar.gz archives to decompress.')
            return
        self.run_backend_action(self.decompress_status_label,'Decompress',lambda api: api.decompress(input_dir))

    def set_up_denoise(self):
        #Set up the Denoise tab (raw PNG -> TIFF conversion, then destriping)
        self.textbox_denoise = ctk.CTkTextbox(self.tabview.tab("Denoise"), width=1000,height=80)
        self.textbox_denoise.insert("0.0", "Denoise converts raw lightsheet PNG stacks to TIFF, then removes striping artifacts.\n"+
                             "LOCAL runs each sample one at a time. SLURM submits a batch job that automatically chains conversion into destriping.")
        self.textbox_denoise.place(relx=0.0005,rely=0.01)
        self.denoise_scratch_entry = ctk.CTkEntry(self.tabview.tab("Denoise"), width=600, placeholder_text="Scratch directory containing lightsheet/raw/<sample> folders.")
        self.denoise_scratch_entry.place(relx=0.01,rely=0.25)
        self.webbtn = ctk.CTkButton(self.tabview.tab("Denoise"),text="Find Scratch Folder",font=FONT_BUTTON,fg_color=SECONDARY_BUTTON["fg_color"],hover_color=SECONDARY_BUTTON["hover_color"],command=lambda: self.select_folder_into_entry(self.denoise_scratch_entry,'Select scratch directory'))
        self.webbtn.place(relx=0.65,rely=0.25)
        self.webbtn = ctk.CTkButton(self.tabview.tab("Denoise"),text="Start Denoising",font=FONT_BUTTON,command=self.start_denoise)
        self.webbtn.place(relx=0.4,rely=0.35)
        self.denoise_status_label = ctk.CTkLabel(self.tabview.tab("Denoise"),text="",font=FONT_STATUS)
        self.denoise_status_label.place(relx=0.01,rely=0.42)

    def start_denoise(self):
        scratch_dir=self.denoise_scratch_entry.get().strip()
        if not scratch_dir:
            self.throw_error('Please select a scratch directory before denoising.')
            return
        self.run_backend_action(self.denoise_status_label,'Denoise',lambda api: api.denoise(scratch_dir),target_path=scratch_dir)

    def set_up_stitch(self):
        #Set up the Stitch tab
        self.textbox_stitch = ctk.CTkTextbox(self.tabview.tab("Stitch"), width=1000,height=80)
        self.textbox_stitch.insert("0.0", "Stitch combines destriped tile images into a single volume per sample.\n"+
                             "On SLURM, you may optionally auto-chain into the next pipeline stage once stitching finishes.")
        self.textbox_stitch.place(relx=0.0005,rely=0.01)
        self.stitch_scratch_entry = ctk.CTkEntry(self.tabview.tab("Stitch"), width=600, placeholder_text="Scratch directory containing lightsheet/destriped/<sample> folders.")
        self.stitch_scratch_entry.place(relx=0.01,rely=0.25)
        self.webbtn = ctk.CTkButton(self.tabview.tab("Stitch"),text="Find Scratch Folder",font=FONT_BUTTON,fg_color=SECONDARY_BUTTON["fg_color"],hover_color=SECONDARY_BUTTON["hover_color"],command=lambda: self.select_folder_into_entry(self.stitch_scratch_entry,'Select scratch directory'))
        self.webbtn.place(relx=0.65,rely=0.25)
        self.stitch_chain_var = tk.BooleanVar(value=False)
        self.stitch_chain_checkbox = ctk.CTkCheckBox(self.tabview.tab("Stitch"),text="Auto-chain to next stage (SLURM only)",variable=self.stitch_chain_var)
        self.stitch_chain_checkbox.place(relx=0.01,rely=0.32)
        self.webbtn = ctk.CTkButton(self.tabview.tab("Stitch"),text="Start Stitching",font=FONT_BUTTON,command=self.start_stitch)
        self.webbtn.place(relx=0.4,rely=0.4)
        self.stitch_status_label = ctk.CTkLabel(self.tabview.tab("Stitch"),text="",font=FONT_STATUS)
        self.stitch_status_label.place(relx=0.01,rely=0.47)

    def start_stitch(self):
        scratch_dir=self.stitch_scratch_entry.get().strip()
        if not scratch_dir:
            self.throw_error('Please select a scratch directory before stitching.')
            return
        chain_next_stage=bool(self.stitch_chain_var.get())
        self.run_backend_action(self.stitch_status_label,'Stitch',lambda api: api.stitch(scratch_dir,chain_next_stage=chain_next_stage),target_path=scratch_dir)

    def set_up_registration(self):
        #Set up the Registration tab
        self.textbox_registration = ctk.CTkTextbox(self.tabview.tab("Registration"), width=1000,height=80)
        self.textbox_registration.insert("0.0", "Registration aligns lightsheet data to a reference atlas.\n"+
                             "LOCAL registers a single sample. SLURM registers a batch of samples and requires a segmentation path and conda environment name.")
        self.textbox_registration.place(relx=0.0005,rely=0.01)
        self.registration_image_entry = ctk.CTkEntry(self.tabview.tab("Registration"), width=600, placeholder_text="Path to stitched image (LOCAL) or parent image folder (SLURM).")
        self.registration_image_entry.place(relx=0.01,rely=0.2)
        self.webbtn = ctk.CTkButton(self.tabview.tab("Registration"),text="Find Image Folder",font=FONT_BUTTON,fg_color=SECONDARY_BUTTON["fg_color"],hover_color=SECONDARY_BUTTON["hover_color"],command=lambda: self.select_folder_into_entry(self.registration_image_entry,'Select image path'))
        self.webbtn.place(relx=0.65,rely=0.2)
        self.registration_output_entry = ctk.CTkEntry(self.tabview.tab("Registration"), width=600, placeholder_text="Output path for registration results.")
        self.registration_output_entry.place(relx=0.01,rely=0.28)
        self.webbtn = ctk.CTkButton(self.tabview.tab("Registration"),text="Find Output Folder",font=FONT_BUTTON,fg_color=SECONDARY_BUTTON["fg_color"],hover_color=SECONDARY_BUTTON["hover_color"],command=lambda: self.select_folder_into_entry(self.registration_output_entry,'Select output path'))
        self.webbtn.place(relx=0.65,rely=0.28)
        self.registration_atlas_entry = ctk.CTkEntry(self.tabview.tab("Registration"), width=600, placeholder_text="Atlas path (LOCAL, optional - default atlas used if left empty).")
        self.registration_atlas_entry.place(relx=0.01,rely=0.36)
        self.webbtn = ctk.CTkButton(self.tabview.tab("Registration"),text="Find Atlas Folder",font=FONT_BUTTON,fg_color=SECONDARY_BUTTON["fg_color"],hover_color=SECONDARY_BUTTON["hover_color"],command=lambda: self.select_folder_into_entry(self.registration_atlas_entry,'Select atlas path'))
        self.webbtn.place(relx=0.65,rely=0.36)
        self.registration_segmentation_entry = ctk.CTkEntry(self.tabview.tab("Registration"), width=600, placeholder_text="Parent segmentation path (required for SLURM batch registration).")
        self.registration_segmentation_entry.place(relx=0.01,rely=0.44)
        self.webbtn = ctk.CTkButton(self.tabview.tab("Registration"),text="Find Segmentation Folder",font=FONT_BUTTON,fg_color=SECONDARY_BUTTON["fg_color"],hover_color=SECONDARY_BUTTON["hover_color"],command=lambda: self.select_folder_into_entry(self.registration_segmentation_entry,'Select parent segmentation path'))
        self.webbtn.place(relx=0.65,rely=0.44)
        self.registration_conda_entry = ctk.CTkEntry(self.tabview.tab("Registration"), width=600, placeholder_text="Conda environment name (required for SLURM batch registration).")
        self.registration_conda_entry.place(relx=0.01,rely=0.52)
        self.webbtn = ctk.CTkButton(self.tabview.tab("Registration"),text="Start Registering",font=FONT_BUTTON,command=self.start_register)
        self.webbtn.place(relx=0.4,rely=0.6)
        self.registration_status_label = ctk.CTkLabel(self.tabview.tab("Registration"),text="",font=FONT_STATUS)
        self.registration_status_label.place(relx=0.01,rely=0.67)

    def start_register(self):
        image_path=self.registration_image_entry.get().strip()
        output_path=self.registration_output_entry.get().strip() or None
        atlas_path=self.registration_atlas_entry.get().strip() or None
        segmentation_path=self.registration_segmentation_entry.get().strip() or None
        conda_env=self.registration_conda_entry.get().strip() or None
        if not image_path:
            self.throw_error('Please select an image path before registering.')
            return
        if self.get_computertype()=='slurm' and (not segmentation_path or not conda_env):
            self.throw_error('SLURM registration requires both a parent segmentation path and a conda environment name.')
            return
        self.run_backend_action(self.registration_status_label,'Register',lambda api: api.register(
            image_path,output_path=output_path,atlas_path=atlas_path,
            parent_segmentation_path=segmentation_path,conda_environment_name=conda_env),target_path=image_path)

    def set_up_segmentation(self):
        #Set up the Segmentation tab
        self.textbox_segmentation = ctk.CTkTextbox(self.tabview.tab("Segmentation"), width=1000,height=80)
        self.textbox_segmentation.insert("0.0", "Segmentation splits stitched volumes into cubes, runs the ilastik pixel classifier, and concatenates cell counts.\n"+
                             "LOCAL requires an ilastik project (.ilp) file. SLURM submits the full batch pipeline.")
        self.textbox_segmentation.place(relx=0.0005,rely=0.01)
        self.segmentation_scratch_entry = ctk.CTkEntry(self.tabview.tab("Segmentation"), width=600, placeholder_text="Scratch directory containing lightsheet/stitched/<sample> folders.")
        self.segmentation_scratch_entry.place(relx=0.01,rely=0.25)
        self.webbtn = ctk.CTkButton(self.tabview.tab("Segmentation"),text="Find Scratch Folder",font=FONT_BUTTON,fg_color=SECONDARY_BUTTON["fg_color"],hover_color=SECONDARY_BUTTON["hover_color"],command=lambda: self.select_folder_into_entry(self.segmentation_scratch_entry,'Select scratch directory'))
        self.webbtn.place(relx=0.65,rely=0.25)
        self.segmentation_ilastik_entry = ctk.CTkEntry(self.tabview.tab("Segmentation"), width=600, placeholder_text="Ilastik project file (.ilp) - required for LOCAL.")
        self.segmentation_ilastik_entry.place(relx=0.01,rely=0.33)
        self.webbtn = ctk.CTkButton(self.tabview.tab("Segmentation"),text="Find .ilp File",font=FONT_BUTTON,fg_color=SECONDARY_BUTTON["fg_color"],hover_color=SECONDARY_BUTTON["hover_color"],command=self.select_ilastik_file)
        self.webbtn.place(relx=0.65,rely=0.33)
        self.webbtn = ctk.CTkButton(self.tabview.tab("Segmentation"),text="Start Segmenting",font=FONT_BUTTON,command=self.start_segment)
        self.webbtn.place(relx=0.4,rely=0.43)
        self.segmentation_status_label = ctk.CTkLabel(self.tabview.tab("Segmentation"),text="",font=FONT_STATUS)
        self.segmentation_status_label.place(relx=0.01,rely=0.5)

    def select_ilastik_file(self):
        filepath = filedialog.askopenfilename(title='Select ilastik project file',initialdir=self.wd,filetypes=[('Ilastik project','*.ilp'),('All files','*.*')])
        if filepath:
            self.segmentation_ilastik_entry.delete(0,tk.END)
            self.segmentation_ilastik_entry.insert(0,filepath)

    def start_segment(self):
        scratch_dir=self.segmentation_scratch_entry.get().strip()
        ilastik_file=self.segmentation_ilastik_entry.get().strip() or None
        if not scratch_dir:
            self.throw_error('Please select a scratch directory before segmenting.')
            return
        if self.get_computertype()=='local' and not ilastik_file:
            self.throw_error('Local segmentation requires an ilastik project (.ilp) file.')
            return
        self.run_backend_action(self.segmentation_status_label,'Segment',lambda api: api.segment(scratch_dir,ilastik_project_file=ilastik_file),target_path=scratch_dir)

    def set_up_custom_script(self):
        self.textbox = ctk.CTkTextbox(self.tabview.tab("Custom Script"), width=1000,height=300)
        self.textbox.insert("0.0", "Implementing Custom Python Scripts in BrainBeam:\n\n" + "To run a custom python script you will need the full path to the sample or directory of samples." +
                            "Please see our example python script (insert location here) in order to match our format. \n\n " +
                            "An example use case is to apply a custom neural network for image segmentation" +
                            "For each stitched sample, data will first be seperated into chunks as specified by you below. \n\n If left empty, the default chunk size is 500x500x500 pixels."+
                            "Once seperated, your function will be applied to each chunk. Then, each chunk will be stitched back together.\n\n The modified stitched files will then be saved in the directory of your choosing." +
                            "For advanced use cases, please use our BrainBeam Command Line Interface (CLI)")
        self.textbox.place(relx=0.0005,rely=0.01)
        self.optionmenu_1 = ctk.CTkOptionMenu(self.tabview.tab("Custom Script"), width=5,values=["Perform on Single Sample", "Perform on Batch of samples"])
        self.optionmenu_1.place(relx=0.35,rely=0.51)
        self.custom_target_entry = ctk.CTkEntry(self.tabview.tab("Custom Script"), width=600, placeholder_text="Full path to single sample's data or directory of samples. Please see our instructions for data org.")
        self.custom_target_entry.place(relx=0.2,rely=0.61)
        self.custom_script_entry = ctk.CTkEntry(self.tabview.tab("Custom Script"), width=600, placeholder_text=r"Full path to python script. Ex. C:\Users\mypython.py ")
        self.custom_script_entry.place(relx=0.2,rely=0.71)
        self.custom_chunk_entry = ctk.CTkEntry(self.tabview.tab("Custom Script"), width=600, placeholder_text=r"Set cubic volume size. Ex. '200' means stitched volume will be applied to 200x200x200 chunks.")
        self.custom_chunk_entry.place(relx=0.2,rely=0.81)
        self.runbutton=ctk.CTkButton(master=self.tabview.tab("Custom Script"),text="Run Custom Script",width =8,command=self.start_custom_script)
        self.runbutton.place(relx=0.6,rely=0.91)
        self.registerbutton=ctk.CTkButton(master=self.tabview.tab("Custom Script"),text="Register Custom Script to Overview",width =8,command=self.register_custom_script)
        self.registerbutton.place(relx=0.2,rely=0.91)
        self.custom_status_label = ctk.CTkLabel(self.tabview.tab("Custom Script"),text="",font=FONT_STATUS)
        self.custom_status_label.place(relx=0.2,rely=0.96)

    def start_custom_script(self):
        target_path=self.custom_target_entry.get().strip()
        script_path=self.custom_script_entry.get().strip()
        if not target_path or not script_path:
            self.throw_error('Please provide both a data path and a custom script path.')
            return
        self.run_backend_action(self.custom_status_label,'Custom',lambda api: api.custom(script_path,target_path),target_path=target_path)

    def register_custom_script(self):
        #Marks the Custom Script stage as complete in the overview for the given sample/batch
        #without re-running it, e.g. for scripts that were already run outside the GUI.
        target_path=self.custom_target_entry.get().strip()
        if not target_path:
            self.throw_error('Please provide the data path to register before adding it to the overview.')
            return
        self.update_sample_status(target_path,'Custom','complete')
        self.custom_status_label.configure(text='Custom Script: registered to overview.')

    def set_up_radio_buttons(self):
        # create radiobutton frame
        self.radio_var = tk.StringVar(value=0)
        self.label_radio_group = ctk.CTkLabel(master=self.sidebar_frame, text="Analysis Location:",font=('Arial',17,'bold'))
        self.label_radio_group.place(relx=0.9,rely=0.18,anchor='e')
        self.radio_button_1 = ctk.CTkRadioButton(master=self.sidebar_frame, text='LOCAL',font=('Arial',15,'bold'),variable=self.radio_var, value=0)
        self.radio_button_1.place(relx=0.68,rely=0.21,anchor='e')
        self.radio_button_2 = ctk.CTkRadioButton(master=self.sidebar_frame, text='SLURM HPC',font=('Arial',15,'bold'), variable=self.radio_var, value=1)
        self.radio_button_2.place(relx=0.78,rely=0.24,anchor='e')
        self.radio_button_3 = ctk.CTkRadioButton(master=self.sidebar_frame,text='AWS',font=('Arial',15,'bold'),variable=self.radio_var, value=2)
        self.radio_button_3.place(relx=0.68,rely=0.27,anchor='e')
    
    def call_logo(self):
        #Set logo image. Path is computed relative to this file so the GUI works
        #regardless of the directory it was launched from. Falls back gracefully if the
        #image asset is ever missing, rather than crashing the whole GUI on startup.
        gui_dir = os.path.dirname(os.path.abspath(__file__))
        image_path = os.path.join(gui_dir, "images", "BBlogoV1.png")
        self.navigation_frame = ctk.CTkFrame(self.root, corner_radius=0,width=180,height=95)
        self.navigation_frame.place(relx=0,rely=0.05)
        self.navigation_frame.grid_rowconfigure(4, weight=1)
        if os.path.exists(image_path):
            self.logo_image = ctk.CTkImage(Image.open(image_path), size=(160, 90))
            self.navigation_frame_label = ctk.CTkLabel(self.navigation_frame, text="", height=10,width=100, image=self.logo_image)
        else:
            self.navigation_frame_label = ctk.CTkLabel(self.navigation_frame, text="BrainBeam", font=FONT_SECTION)
        self.navigation_frame_label.place(relx=0,rely=0.05)

    def __call__(self):
        self.refresh_screen()

    def refresh_screen(self):
        self.root.mainloop()
    
    def copydata(self):
        print('Copying data')


if __name__=='__main__':
    guioh=BrainBeamGuiBase()
    guioh()