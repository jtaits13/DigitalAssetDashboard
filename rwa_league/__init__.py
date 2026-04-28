"""RWA League package.

Keep package import side effects minimal so submodules such as
``rwa_league.explore_nav`` can be imported without triggering the full data stack.
Import symbols from ``rwa_league.client`` or ``rwa_league.widgets`` directly.
"""

__all__: list[str] = []
