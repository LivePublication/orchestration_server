"""
Takes a template programmatic artcile and applies it the 
generated orchestration crate.
"""

import os

def apply_template(output_path):
  """ An extremely simple template application function. """

  # Hard coded directory structure, untill we start parsing the 
  # orchestration crate for the data

  # Create directory for the new version
  new_version = output_path + "New_version"
  os.mkdir(new_version)

  # Copy the template files into the new version
  """
  Req files: 
  - _extensions (dir)
  - index_files (dir)
  - _quarto.yml (file)
  - globus-overview.svg (file)
  - index.qmd (file)
  - references.bib (file)

  All files/dirs are in quarto_templates/LiD
  """
  # Copy the _extensions directory
  os.mkdir(new_version + "/_extensions")
  os.system("cp -r quarto_templates/LiD/_extensions/* " + new_version + "/_extensions")

  # Copy the index_files directory
  os.mkdir(new_version + "/index_files")
  os.system("cp -r quarto_templates/LiD/index_files/* " + new_version + "/index_files")

  # Copy the _quarto.yml file
  os.system("cp quarto_templates/LiD/_quarto.yml " + new_version + "/_quarto.yml")

  # Copy the globus-overview.svg file
  os.system("cp quarto_templates/LiD/globus-overview.svg " + new_version + "/globus-overview.svg")

  # Copy the index.qmd file
  os.system("cp quarto_templates/LiD/index.qmd " + new_version + "/index.qmd")

  # Copy the references.bib file
  os.system("cp quarto_templates/LiD/references.bib " + new_version + "/references.bib")

  # Finally, copy the orchestration crate into the new version
  os.system("cp -r orchestration_crate " + new_version + "/orchestration_crate")

  # Remove the local orchestration crate
  os.system("rm -r orchestration_crate")

