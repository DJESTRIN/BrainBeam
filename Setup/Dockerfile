# Use an official Continuum Analytics Docker image as a parent image
FROM continuumio/miniconda3

# Set working directory
WORKDIR /app

# Copy the environment files for each Conda environment
COPY env1.yml /app/env1.yml
COPY env2.yml /app/env2.yml
COPY env3.yml /app/env3.yml
COPY env4.yml /app/env4.yml
COPY env5.yml /app/env5.yml

# Install the environments
RUN conda env create -f /app/env1.yml && conda clean -a
RUN conda env create -f /app/env2.yml && conda clean -a
RUN conda env create -f /app/env3.yml && conda clean -a
RUN conda env create -f /app/env4.yml && conda clean -a
RUN conda env create -f /app/env5.yml && conda clean -a

# Copy your pipeline scripts into the container
COPY . /app

# Activate environment and set PATH for subsequent commands
SHELL ["conda", "run", "-n", "base", "/bin/bash", "-c"]

# Optional: Set the default command to run your pipeline
CMD ["bash", "run_pipeline.sh"]
