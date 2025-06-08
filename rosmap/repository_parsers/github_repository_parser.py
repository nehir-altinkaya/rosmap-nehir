from rosmap.api_bindings.github_api_bindings import GithubApiBindings
from .i_repository_parser import IRepositoryParser

print("IN PARSER github_repository_parser.py has been loaded")

class GithubRepositoryParser(IRepositoryParser):
    """
    Parses repository-URLs from GitHub using the GitHub-search API.
    """
    def __init__(self, settings: dict):
        """
        Creates a new instance of the GithubRepositoryParser class.
        :param settings: Settings dict containing keys github_username, github_password (token works as well), as well as
        search-API rate limit.
        """
        self.__api_bindings = GithubApiBindings(settings["github_username"],
                                                settings["github_password"],
                                                settings["github_search_rate_limit"])
        self.__settings = settings

    def parse_repositories(self, repository_dict: dict) -> None:
        print("=== Inside parse_repositories ===")
        input("Pause here to inspect...")
        # Github only hosts git repositories.
        repository_dict["git"].update(self.__api_bindings.get_urls_of_topic(self.__settings["github_search_topic"]))
        print("=== Finished parse_repositories ===")
        input("Pause here to inspect for after parsing...")