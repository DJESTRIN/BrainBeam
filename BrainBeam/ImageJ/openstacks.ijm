// Macro to recursively find and open all TIFF sequences as virtual stacks

// Root directory to start searching
rootDirectory = "/athena/listonlab/scratch/dje4001/lightsheet_cluster/rabies_cort_control_cohort2/lightsheet/stitched/";

// Function to process TIFF sequences in a directory
function processDirectory(directory) {
    fileList = getFileList(directory);

    // Loop through all files and directories in the current directory
    for (i = 0; i < fileList.length; i++) {
        file = fileList[i];
        path = directory + file;

        // If it's a directory, recursively process it
        if (File.isDirectory(path)) {
            processDirectory(path + "/");
        }
        // If it's a TIFF file, check if it matches a sequence pattern
        else if (endsWith(file, ".tif")) {
            processTIFFSequence(directory);
            return; // Process only one sequence per directory to avoid redundant openings
        }
    }
}

// Function to find and open TIFF sequences
function processTIFFSequence(directory) {
    // Assuming the TIFF files follow a sequential naming pattern
    // Adjust the pattern as needed to match your files
    filePattern = "*.tif";

    // Find all TIFF files in the directory
    fileList = getFileList(directory + filePattern);

    // Check if the sequence pattern is detected
    if (fileList.length > 0) {
        // Create a virtual stack from the TIFF sequence
        open("tiff", directory + filePattern, "useVirtual");

        // Optionally, set the title of the virtual stack window
        setTitle("Virtual Stack: " + directory);
    }
}

// Start processing from the root directory
processDirectory(rootDirectory);
