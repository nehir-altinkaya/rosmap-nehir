#!/usr/bin/env python3
import argparse
import json
import os
import logging
from rosmap.loaders.module_loader import ModuleLoader
from shutil import copy
from rosmap.repository_parsers.github_repository_parser import GithubRepositoryParser


PROGRAM_DESCRIPTION = ""


def load_parsers(settings: dict) -> list:
    return ModuleLoader.load_modules(os.path.dirname(os.path.realpath(__file__)),
                                        "repository_parsers",
                                        settings["parsers"],
                                        ["IRepositoryParser"],
                                        "RepositoryParser",
                                        settings)


def load_cloners(settings: dict) -> dict:
    cloners = dict()
    for cloner in ModuleLoader.load_modules(os.path.dirname(os.path.realpath(__file__)),
                                            "repository_cloners",
                                            ["IRepositoryCloner"],
                                            "RepositoryCloner",
                                            settings):
        cloners[cloner.clones()] = cloner
    return cloners


def load_package_analyzers(settings: dict) -> list:
    return ModuleLoader.load_modules(os.path.dirname(os.path.realpath(__file__)),
                                              "package_analyzers",
                                              ["PackageAnalyzer"],
                                              "Analyzer",
                                              settings)


def load_file_analyzers() -> list:
    return ModuleLoader.load_modules(os.path.dirname(os.path.realpath(__file__)),
                                 "file_analyzers",
                                 ["IFileAnalyzer"],
                                 "FileAnalyzer")


def load_analyzers(settings: dict) -> dict:
    analyzers = dict()
    for analyzer in ModuleLoader.load_modules(os.path.dirname(os.path.realpath(__file__)),
                                              "repository_analyzers/offline",
                                              ["IRepositoryAnalyzer", "AbstractRepositoryAnalyzer"],
                                              "RepositoryAnalyzer",
                                              load_package_analyzers(settings),
                                              load_file_analyzers()):
        analyzers[analyzer.analyzes()] = analyzer
    return analyzers


def load_remote_analyzers(settings: dict) -> dict:
    remote_analyzers = dict()
    for analyzer in ModuleLoader.load_modules(os.path.dirname(os.path.realpath(__file__)),
                                              "repository_analyzers/online",
                                              ["ISCSRepositoryAnalyzer"],
                                              "RepositoryAnalyzer",
                                              settings):
        remote_analyzers[analyzer.analyzes()] = analyzer
    return remote_analyzers


def write_to_file(path, repo_details):
    print(f"Writing repository details to {path}")
    with open(path, "w") as output_file:
        json.dump(list(repo_details.values()), output_file, indent=4)
    output_file.close()


def main():
    #added this to see if the main function is called
    def main():
        try:
            print("=== MAIN STARTED ===")
        except Exception as e:
            print(f"An error occurred: {e}")
    print("Running:", __file__)

    parser = argparse.ArgumentParser(description=PROGRAM_DESCRIPTION)
    parser.add_argument("--config", "-c", help="Add a path to the config.json file that contains, usernames, api-tokens and settings.", default=os.path.dirname(os.path.realpath(__file__)) + "/config/config.json")
    parser.add_argument("--load_existing", "-l", help="Use this flag to load previous link-files from workspace.", default=False, action="store_true")
    parser.add_argument("--skip_download", "-d", help="Use this flag to skip downloading of repositories to your workspace.", default=False, action="store_true")
    parser.add_argument("--output", "-o", help="Add a path to the output file for the analysis. If this path is not defined, analysis will not be performed. ", default="")
    parser.add_argument("--generate_config", help="Generates a config file on the given path.")

    # Parse arguments
    arguments = parser.parse_args()
    print("Arguments:", arguments)

    # Set up logger
    logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)

    if arguments.generate_config is not None:
        copy(os.path.dirname(os.path.realpath(__file__)) + "/config/config.json", arguments.generate_config)
        return 0

    # Warn user that output has to be set to analyze:
    if arguments.output == "":
        logging.warning("parameter --output has not been defined, analysis will be skipped, add --output <path> to perform analysis.")

    # Load settings.
    configfile = open(arguments.config, "r")
    settings = json.loads(configfile.read())
    print("=== SETTINGS LOADED ===")
    print("settings are: ", settings)

    # Expand home directories.
    settings["analysis_workspace"] = os.path.expanduser(settings["analysis_workspace"])
    settings["rosdistro_workspace"] = os.path.expanduser(settings["rosdistro_workspace"])

    # Initialize dictionaries.
    repositories = dict()
    for vcs in settings["version_control_systems"]:
        repositories[vcs] = set()

    parser = GithubRepositoryParser({
        'github_username': 'nehir-altinkaya',
        'github_password': '',
        'github_search_topic': 'ros2',
        'github_search_rate_limit': 1000,
        'parsers': ['GithubRepositoryParser'],
        'version_control_systems': ['git', 'svn', 'hg'],
        "rosdistro_repo_parser": {
            "rosdistro_url": "https://github.com/ros/rosdistro",
            "rosdistro_workspace": "~/.rosdistro_workspace"
        },
        'analysis_workspace': '~/.analysis_workspace',
        'repository_folder': 'repositories/',
        "version_control_systems": ["git","svn","hg"],
        'rosdistro_workspace': '~/.rosdistro_workspace',
        'parsers': ['GithubRepositoryParser', 'RosdistroRepositoryParser'],
        'repository_cloners': ['GitRepositoryCloner', 'SvnRepositoryCloner', 'HgRepositoryCloner'],
        'repository_analyzers': ['GitRepositoryAnalyzer', 'SvnRepositoryAnalyzer', 'HgRepositoryAnalyzer'],
        'package_analyzers': ['PackageAnalyzer'],
        'file_analyzers': ['FileAnalyzer'],
        'social_coding_sites': ['github']
        })
    parser.parse_repositories(repository_dict=repositories)

    if not arguments.load_existing:
        # Parse repositories
        logging.info("[Parser]: Parsing repositories...")
        parsers = load_parsers(settings)
        for parser in parsers:
            parser.parse_repositories(repositories)

        # Create folder
        links_dir = os.path.join(os.path.expanduser(settings["analysis_workspace"]), "links")
        os.makedirs(links_dir, exist_ok=True)

        # Write to file.
        logging.info("[Parser]: Writing repository links to file...")
        for vcs, repository_set in repositories.items():
            logging.info("[Parser]: Writing file for " + vcs)
            #changed here to use os.path.join for better path handling
            with open(os.path.join(settings["analysis_workspace"], "links", vcs), "w+") as output_file:
                for repository in repository_set:
                    output_file.write(repository + "\n")
    else:
        for vcs in settings["version_control_systems"]:
            with open(settings["analysis_workspace"]+"/links/" + vcs, "r") as output_file:
                for line in output_file:
                    repositories[vcs].add(line.rstrip("\r\n"))

    if not arguments.skip_download:
        cloners = load_cloners(settings)
        print("=== CLONERS LOADED ===")

        logging.info("[Cloner]: Cloning repositories...")
        print(f"Calling clone_repositories for VCS {vcs} with {len(repositories[vcs])} repositories.") 
        for vcs in settings["version_control_systems"]:
            if vcs in cloners:
                sorted_repos = sorted(repositories[vcs])  # Convert set to sorted list
                selected_repos = sorted_repos[1753:1953]    # Get only the 200 after the first 1753
                cloners[vcs].clone_repositories(selected_repos)
            else:
                logging.warning("[Cloner]: Cannot clone repositories of type " + vcs + ": No cloner found for this type...")

    if not arguments.output == "":
        analyzers = load_analyzers(settings)
        repo_details = dict()
        for vcs in settings["version_control_systems"]:
            if vcs in analyzers:
                analyzers[vcs].analyze_repositories(settings["analysis_workspace"] + settings["repository_folder"] + vcs,
                                                    repo_details)
            else:
                logging.warning("Cannot analyze repositories of type " + vcs + ": No analyzer found for this type...")

            if repo_details:
                logging.info("Writing analysis results to output.json...")
                write_to_file(arguments.output, repo_details)
            else:
                logging.warning("No analysis results to write. output.json will not be created.")  
        write_to_file(arguments.output, repo_details)

   
        

        logging.info("Starting to parse repositories...")
        pars = load_parsers(settings)
        for parser in pars:
            parser.parse_repositories(repositories)
            logging.info("Finished parsing repositories.")
            logging.info("Found the following repositories:")

        for vcs, repo_set in repositories.items():
            logging.info(f"VCS: {vcs}, Repositories: {len(repo_set)}")
            
        # Log number of repositories found per VCS
        for vcs, repo_set in repositories.items():
            logging.info(f"VCS: {vcs}, Repositories: {len(repo_set)}")
            
        remote_analyzers = load_remote_analyzers(settings)
        for scs in settings["social_coding_sites"]:
            if scs in remote_analyzers:
                remote_analyzers[scs].analyze_repositories(repo_details)
            else:
                logging.warning("Cannot analyze scs of type " + scs + ": No analyzer found for this type...")

            if repo_details:
                logging.info("Writing analysis results to output.json...")
                write_to_file(arguments.output, repo_details)
            else:
                logging.warning("No analysis results to write. output.json will not be created.")
                
        write_to_file(arguments.output, repo_details)

    logging.info("Actions finished. Exiting.")

#calling main function as it wasnt done before
if __name__ == "__main__":
    print("=== MAIN STARTED ===")
    main()





