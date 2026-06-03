## [v3.1.0](https://github.com/DopamineStudios/beacon/compare/vv3.0.1...vv3.1.0) (2026-05-26)
### Features & Minor Updates and Changes

* Owner Message containing the file is now automatically deleted upon successful upload. ([abdb118](https://github.com/DopamineStudios/beacon/commit/abdb1180ee515b375c9b510c6152dc00d7f0728d))

### Documentation Changes

* Updated README. ([1efc9b1](https://github.com/DopamineStudios/beacon/commit/1efc9b12702e6c7e0aa481a40d4d24d74c7b943f))

## [v3.0.1](https://github.com/DopamineStudios/beacon/compare/vv3.0.0...vv3.0.1) (2026-05-26)
### Bug Fixes

* Updated default colour to new colour scheme of Beacon. ([e251343](https://github.com/DopamineStudios/beacon/commit/e2513436822f0ed0c0054798344dda30e5e8df81))

### Documentation Changes

* Fixed README images. ([20db122](https://github.com/DopamineStudios/beacon/commit/20db122b1af92bfbec1a1ff9701a754e75d6c353))

## [v3.0.0](https://github.com/DopamineStudios/dopamine-framework/compare/vv2.2.2...vv2.3.0) (2026-05-25)
### ⚠ BREAKING CHANGES

* Re-named Dopamine Framework to Beacon.

### Features & Minor Updates and Changes

* New "Upload Module" button in Owner Dashboard that allows uploading modules/cogs directly through Discord. Extremely useful for people hosting their bot through platforms like Render that don't allow modifying files without completely re-deploying and restarting the process, which would make hot-reloading useless. ([0e39211](https://github.com/DopamineStudios/dopamine-framework/commit/0e392118fc635d1a772701c1c6ca096cff3a3af4))
* Re-named Dopamine Framework to Beacon. ([a14242d](https://github.com/DopamineStudios/dopamine-framework/commit/a14242db1337ff8cf5e644847912902114e7f745))

### Documentation Changes

* Updated docs ([3b957ec](https://github.com/DopamineStudios/dopamine-framework/commit/3b957ecb174eaef39547f31fd7565948d726c624))

## [v2.2.2](https://github.com/smite-codes/beacon/compare/vv2.2.1...vv2.2.2) (2026-05-11)
### Bug Fixes

* (Hotfix): Fixed crash caused by from_rgb expecting individual r, g, b values but getting tuple instead. ([728102c](https://github.com/smite-codes/beacon/commit/728102c13e1390f8e844deada0d1e169e0eb141c))
* Bot class now allows editing the self.logger directly. ([082e0fc](https://github.com/smite-codes/beacon/commit/082e0fc450ed0e798ac45b580b4a90e750b67d7a))
* Fixed font loading error. ([a4ea547](https://github.com/smite-codes/beacon/commit/a4ea547d21869778ad6734c2e2c5a67a1f2e2a90))

### Documentation Changes

* Updated Documentation. ([d235048](https://github.com/smite-codes/beacon/commit/d2350483ca8f7fcf63c4fb63fd2811065dbb2be4))

## [v2.2.1](https://github.com/smite-codes/beacon/compare/vv2.2.0...vv2.2.1) (2026-05-11)
### Bug Fixes

* (Hotfix): Fixed crash caused by wrong usage of relative imports in internal cogs. ([9e16217](https://github.com/smite-codes/beacon/commit/9e16217db5fb3011a0760c22a6447ff0f966e0c1))

## [v2.2.0](https://github.com/smite-codes/beacon/compare/vv2.1.1...vv2.2.0) (2026-05-11)
### Features & Minor Updates and Changes

* Added ability to customise the accent colour of latency graph and ping embed. ([3275827](https://github.com/smite-codes/beacon/commit/32758272db0daa7538f7c4b4e7a0c485f56e946b))
* Updated all internal commands (`/ping`, `/latency graph`, and `/od`) to use Beacon Commands. ([37e5111](https://github.com/smite-codes/beacon/commit/37e5111ba6db5262bc5e6a9787a220fa5409a4d1))

### Bug Fixes

* Added missing separator between page number display and navigation buttons. ([085ef59](https://github.com/smite-codes/beacon/commit/085ef591916ec4b826533d96e109817a69eac0b7))

### Documentation Changes

* Updated description for PyPi package. ([bef9a6b](https://github.com/smite-codes/beacon/commit/bef9a6b9bde4d1629be38293b94282e8071bcb2f))
* Updated Documentation. ([29b5fce](https://github.com/smite-codes/beacon/commit/29b5fce7df5f0633eb08339b0a4eb71f4a617d96))
* Updated README. ([7c789a5](https://github.com/smite-codes/beacon/commit/7c789a5192f652a4f41b6d49a0f586bcea58094e))

## [v2.1.1](https://github.com/smite-codes/beacon/compare/vv2.1.0...vv2.1.1) (2026-04-09)
### Bug Fixes

* Hotfix: Fixed preconditions not working at all in command groups. It was caused by adding them to the GROUP instead of the COMMANDS inside it. ([2c28b6c](https://github.com/smite-codes/beacon/commit/2c28b6cddc87d729b0fa9eaa1ac1b6bf3ce35fae))

## [v2.1.0](https://github.com/smite-codes/beacon/compare/vv2.0.2...vv2.1.0) (2026-04-09)
### Features & Minor Updates and Changes

* retry_after in error message for cooldown is now rounded to nearest whole number instead of one showing decimal place. ([d03be00](https://github.com/smite-codes/beacon/commit/d03be008f7484110fcd67357eb62dce04a656f5c))

### Documentation Changes

* Updated README. ([4488ea0](https://github.com/smite-codes/beacon/commit/4488ea0d736e646fdf6b750b2c290ae8f3a1dcb7))

## [v2.0.2](https://github.com/smite-codes/beacon/compare/vv2.0.1...vv2.0.2) (2026-04-09)
### Bug Fixes

* Hotfix: Fixed error in... error handler for command rate limiter. ([c971ad6](https://github.com/smite-codes/beacon/commit/c971ad6309c5041b37e4696a61eefa93da364e94))

## [v2.0.1](https://github.com/smite-codes/beacon/compare/vv2.0.0...vv2.0.1) (2026-04-09)
### Bug Fixes

* Hotfix: Fixed crash in Beacon Commands cooldown due a problem related to the "bucket". ([28e3309](https://github.com/smite-codes/beacon/commit/28e3309582082443ca755ebe0c637f5d3f8f483b))

## [v2.0.0](https://github.com/smite-codes/beacon/compare/vv1.6.0...vv2.0.0) (2026-04-09)
### ⚠ BREAKING CHANGES

* Dropped legacy support.
* New preconditions feature!

### Features & Minor Updates and Changes

* Added documentation for preconditions. ([b665766](https://github.com/smite-codes/beacon/commit/b6657667b79ed0bd08d928759db17aa442c13338))
* Dropped legacy support for importing with the name `dopamine_framework`. Now, only `beacon` works. ([dcf30dc](https://github.com/smite-codes/beacon/commit/dcf30dc75639ba72dae8949425c844c17cb969bf))
* Host Device Battery Status in diagnostics `/ping` embed is now completely hidden if there's no battery. ([d8e6e4d](https://github.com/smite-codes/beacon/commit/d8e6e4dfa1f84394e2c21704577a8a073f88fd9f))
* New preconditions feature! ([ab5fd0f](https://github.com/smite-codes/beacon/commit/ab5fd0f50208c7a977af040dca7629a1e79999e3))

### Documentation Changes

* Added ability to choose whether to disable useless member caching. ([8dc7f23](https://github.com/smite-codes/beacon/commit/8dc7f2316e61a9f1eee781f6cf5253ea2ee1507a))
* Added docstrings to all classes and functions. ([059d475](https://github.com/smite-codes/beacon/commit/059d47587036860b46fb055c9b1a6519935fe647))
* Added documentation for Beacon Commands. ([be1bc43](https://github.com/smite-codes/beacon/commit/be1bc430107ad1f0a5096d81c3c8d9abca3abe40))
* Updated documentation for bot.py. ([e8a7fe3](https://github.com/smite-codes/beacon/commit/e8a7fe3f92a3b0bb45d89aa381ae2cb9dce8716b))
* Updated README ([42f0f40](https://github.com/smite-codes/beacon/commit/42f0f404720788dcabba3fb6f60eda790a266dca))

## [v1.6.0](https://github.com/smite-codes/beacon/compare/vv1.5.0...vv1.6.0) (2026-04-08)
### Features & Minor Updates and Changes

* Banner now displays count of number of cogs loaded. ([3460bb9](https://github.com/smite-codes/beacon/commit/3460bb9b498b8b109947326793f7368f68eb3e60))
* Bot loaded banner is now printed into the logger as well, instead of just the console like before. ([5ce4cd0](https://github.com/smite-codes/beacon/commit/5ce4cd0ff5b30c25709f478e355a490642c69dbe))
* String printed into logger upon skipping sync is now more verbose, matching the one shown inside Discord in Owner Dashboard. ([5abaff5](https://github.com/smite-codes/beacon/commit/5abaff55de0b4cb9af0d59c752d6d5c3b9528724))

## [v1.5.0](https://github.com/smite-codes/beacon/compare/vv1.4.28...vv1.5.0) (2026-03-03)
### Features & Minor Updates and Changes

* Updated ViewPaginator to handle the chunking itself. ([686b853](https://github.com/smite-codes/beacon/commit/686b853e404b59e121e7f7e6de273e7278bad570))

## [v1.4.28](https://github.com/smite-codes/beacon/compare/vv1.4.27...vv1.4.28) (2026-03-03)
### Bug Fixes

* Fixed missing logic to disable the buttons in appropriate situations. ([bf58503](https://github.com/smite-codes/beacon/commit/bf585032a612576b789636c3f19419b6b1dcc8f4))

## [v1.4.27](https://github.com/smite-codes/beacon/compare/vv1.4.26...vv1.4.27) (2026-02-26)
### Bug Fixes

* Removed internal cogs from the reload all cogs button. ([189e66a](https://github.com/smite-codes/beacon/commit/189e66abf7e7cf484ffb3885529e9d0299837f9f))

### Documentation Changes

* Updated readme. ([8ad9495](https://github.com/smite-codes/beacon/commit/8ad94955cad5dacc0231ada241449665a2597a65))

## [v1.4.26](https://github.com/smite-codes/beacon/compare/vv1.4.25...vv1.4.26) (2026-02-26)
### Bug Fixes

* Fixed line break ([f5b6a56](https://github.com/smite-codes/beacon/commit/f5b6a5640e96dbd5bfcee35b96b25658191076b3))

## [v1.4.25](https://github.com/smite-codes/beacon/compare/vv1.4.24...vv1.4.25) (2026-02-26)
### Bug Fixes

* Added s to the second string ([ff55f88](https://github.com/smite-codes/beacon/commit/ff55f8831b408352594df9dfe104f9c244a9814f))
* Made the return statement more verbose ([3ee421c](https://github.com/smite-codes/beacon/commit/3ee421c36ba70f5a95fe84d3c0d6ecc8971f1790))

## [v1.4.24](https://github.com/smite-codes/beacon/compare/vv1.4.23...vv1.4.24) (2026-02-26)
### Bug Fixes

* Fixed return statement ([719a237](https://github.com/smite-codes/beacon/commit/719a237c673210a8a88f9053e16d7677b99a926a))

## [v1.4.23](https://github.com/smite-codes/beacon/compare/vv1.4.22...vv1.4.23) (2026-02-26)
### Bug Fixes

* Fixed return statement ([837ae81](https://github.com/smite-codes/beacon/commit/837ae8108b62053f51a94e74ce17479d4f94edd2))

## [v1.4.22](https://github.com/smite-codes/beacon/compare/vv1.4.21...vv1.4.22) (2026-02-26)
### Bug Fixes

* Finally fixed command sync always being triggered even with no changes by comparing local last synced hash with local now hash. No need for API calls now ([6bab338](https://github.com/smite-codes/beacon/commit/6bab33887488f493e4de73f5e86d5508af45fab6))

## [v1.4.21](https://github.com/smite-codes/beacon/compare/vv1.4.20...vv1.4.21) (2026-02-26)
### Bug Fixes

* Finally fixed command sync always being triggered even with no changes ([b2bbc39](https://github.com/smite-codes/beacon/commit/b2bbc39caf52d040fc366701f8a48b24f8770e5d))

## [v1.4.20](https://github.com/smite-codes/beacon/compare/vv1.4.19...vv1.4.20) (2026-02-26)
### Bug Fixes

* Hotfix: Fixed: `ERROR: Failed to start the bot: Object of type locale_str is not JSON serializable` ([496d853](https://github.com/smite-codes/beacon/commit/496d853577e66c11dac9fb8d8b717e2f1faba2fa))

## [v1.4.19](https://github.com/smite-codes/beacon/compare/vv1.4.18...vv1.4.19) (2026-02-26)
### Bug Fixes

* Hotfix: Fixed error `Failed to start the bot: 'Command' object has no attribute 'type'` ([3f7b2eb](https://github.com/smite-codes/beacon/commit/3f7b2eb0d363cc292eec63649b1bbac1e6a7f5ee))

## [v1.4.18](https://github.com/smite-codes/beacon/compare/vv1.4.17...vv1.4.18) (2026-02-26)
### Bug Fixes

* Switched to hashing to fix command sync always being triggered ([6ab4149](https://github.com/smite-codes/beacon/commit/6ab41496217d9a8cda9e9c57e3a0b2ec591d801c))

## [v1.4.17](https://github.com/smite-codes/beacon/compare/vv1.4.16...vv1.4.17) (2026-02-26)
### Bug Fixes

* Finally fixed command sync always being triggered ([ce9fdf1](https://github.com/smite-codes/beacon/commit/ce9fdf1ee5510649a1f77291f5029c9bdd0b0f4e))

## [v1.4.16](https://github.com/smite-codes/beacon/compare/vv1.4.15...vv1.4.16) (2026-02-26)
### Bug Fixes

* Fixed command sync always being triggered ([0adf0f7](https://github.com/smite-codes/beacon/commit/0adf0f7b76b57de9f9eae1aa471ae57c2efe2fab))

## [v1.4.15](https://github.com/likerofturtles/beacon/compare/vv1.4.14...vv1.4.15) (2026-02-19)
### Bug Fixes

* Fixed sync buttons in owner dashboard. ([2856a58](https://github.com/likerofturtles/beacon/commit/2856a58afd0d58bbf0e86351f5972542b483d5b5))

## [v1.4.14](https://github.com/likerofturtles/beacon/compare/vv1.4.13...vv1.4.14) (2026-02-18)
### Bug Fixes

* Fixed API latency cache freezing and never recovering due to waiting forever for response. (Waiting forever for a response from someone who won't ever respond, instead of moving on? Sounds a lot like my life and she- uhm sorry, where were we?) ([b865b47](https://github.com/likerofturtles/beacon/commit/b865b471599e22dceae9176d8ce9dd0d80f9a581))

## [v1.4.13](https://github.com/likerofturtles/beacon/compare/vv1.4.12...vv1.4.13) (2026-02-14)
### Bug Fixes

* Hotfix: Fixed the error: Failed to start the bot: 'Command' object has no attribute 'type' ([cf09a04](https://github.com/likerofturtles/beacon/commit/cf09a0436b0fa3a7d3a9e01db9d359eb810aad2c))

## [v1.4.12](https://github.com/likerofturtles/beacon/compare/vv1.4.11...vv1.4.12) (2026-02-14)
### Bug Fixes

* Fixed and added ability to handle message commands. ([67eff45](https://github.com/likerofturtles/beacon/commit/67eff4523c8248f069813779202f390df0831e83))

## [v1.4.11](https://github.com/likerofturtles/beacon/compare/vv1.4.10...vv1.4.11) (2026-02-14)
### Bug Fixes

* Hotfix: Updated log file button to use trailing approach because trying to send the whole file to discord just isn't working. ([9004f75](https://github.com/likerofturtles/beacon/commit/9004f75f4513305e92bcf647a2481bfc575c7f14))

## [v1.4.10](https://github.com/likerofturtles/beacon/compare/vv1.4.9...vv1.4.10) (2026-02-14)
### Bug Fixes

* Hotfix: Changed error message to followup because interaction was already responded to. ([452c6d2](https://github.com/likerofturtles/beacon/commit/452c6d25b14a14272940c3e04cd74ec4f58f61e2))

## [v1.4.9](https://github.com/likerofturtles/beacon/compare/vv1.4.8...vv1.4.9) (2026-02-14)
### Bug Fixes

* Added interaction defer for log button. ([d6a1fcf](https://github.com/likerofturtles/beacon/commit/d6a1fcf1e097571ec0768d9a63d8190130811145))

## [v1.4.8](https://github.com/likerofturtles/beacon/compare/vv1.4.7...vv1.4.8) (2026-02-14)
### Bug Fixes

* Hotfix: Fixed the error: Beacon: ERROR: Failed to read log: seek of closed file. ([0e91423](https://github.com/likerofturtles/beacon/commit/0e91423bc5b74d91db1e9b31fc57542cf541a4bf))

## [v1.4.7](https://github.com/likerofturtles/beacon/compare/vv1.4.6...vv1.4.7) (2026-02-14)
### Bug Fixes

* Fixed "show log" button only showing the first 50-60 lines of the log. ([2eb0a07](https://github.com/likerofturtles/beacon/commit/2eb0a07c59912a1083e0c73df3e12b6d8cd55018))

## [v1.4.6](https://github.com/likerofturtles/beacon/compare/vv1.4.5...vv1.4.6) (2026-02-14)
### Bug Fixes

* Fixed "error" unloading in main unloading of extensions because the extension is already manually unloaded. ([93bfdf9](https://github.com/likerofturtles/beacon/commit/93bfdf9266e82f7c19f3f9c388d9dd6c40fa3b07))
* Hotfix: Updated status and activity updater code to use new variables (bug caused by old fix) ([be6f0a8](https://github.com/likerofturtles/beacon/commit/be6f0a814400a10df7ea2e283e588d2cda029de2))

## [v1.4.5](https://github.com/likerofturtles/beacon/compare/vv1.4.4...vv1.4.5) (2026-02-14)
### Bug Fixes

* Added separate unloading for internal cogs so they don't show up mixed with user's cogs during shutdown. ([cf16529](https://github.com/likerofturtles/beacon/commit/cf16529b00300cacbc13c926b38db784665124a1))

## [v1.4.4](https://github.com/likerofturtles/beacon/compare/vv1.4.3...vv1.4.4) (2026-02-14)
### Bug Fixes

* Hotfix: Fixed shutdown and restart buttons not working in owner's dashboard. ([1ce4af9](https://github.com/likerofturtles/beacon/commit/1ce4af9aaa574ceefcdd38b1afcd34267aa600c6))

## [v1.4.3](https://github.com/likerofturtles/beacon/compare/vv1.4.2...vv1.4.3) (2026-02-14)
### Bug Fixes

* Hotfix: Fixed conflict with commands.Bot internal "status" object ([1e3f616](https://github.com/likerofturtles/beacon/commit/1e3f61619f7802221b672ac7bc49ae19d6dc2af3))

## [v1.4.2](https://github.com/likerofturtles/beacon/compare/vv1.4.1...vv1.4.2) (2026-02-13)
### Bug Fixes

* Hotfix: Added line to load the pic.py (i forgot it :sob:) ([347378b](https://github.com/likerofturtles/beacon/commit/347378b4e054c0d1d3c394017d7f3a0271ebb208))

## [v1.4.1](https://github.com/likerofturtles/beacon/compare/vv1.4.0...vv1.4.1) (2026-02-13)
### Bug Fixes

* Hotfix: Added return statements to views that got lost (shorthand for: i accidentally removed it on purpose) while porting to Beacon. ([5866e83](https://github.com/likerofturtles/beacon/commit/5866e83f0d6902a8864d5a1450bf7eba40d874c4))

### Documentation Changes

* Centered the ticks and crosses and stuff column in the comparison table. ([2cf2f95](https://github.com/likerofturtles/beacon/commit/2cf2f956c4ce70cda50212c4680fab61ee7f101d))
* New DOCUMENTATION folder that contains documentation for devs for how to use each feature or utility. ([e358662](https://github.com/likerofturtles/beacon/commit/e358662b7cf51a411ce2df1883676892e4decb49))
* Removed redundant logging documentation from readme. ([061a342](https://github.com/likerofturtles/beacon/commit/061a3426bab9b65ecda6ddefdee6b88ea8633328))

## [v1.4.0](https://github.com/likerofturtles/beacon/compare/vv1.3.3...vv1.4.0) (2026-02-13)
### Features & Minor Updates and Changes

* Added ability to set status and activity when calling Bot. ([456eafa](https://github.com/likerofturtles/beacon/commit/456eafa29d464fc987bacddaed77022e9b3c951c))

## [v1.3.3](https://github.com/likerofturtles/beacon/compare/vv1.3.2...vv1.3.3) (2026-02-13)
### Bug Fixes

* Moved owner dashboard command to a new pic.py (PIC = Permanent Internal Cog) so that owner dashboard doesn't get disabled if the user disables the diagnostics feature. ([efdc633](https://github.com/likerofturtles/beacon/commit/efdc6332c43311fd028588e7a2632ef622026c62))

### Documentation Changes

* Added "No tantrums over different structure" as a feature in readme comparison table. ([ff1dafb](https://github.com/likerofturtles/beacon/commit/ff1dafbdc218742189412a51f651402bd69a632a))

## [v1.3.2](https://github.com/likerofturtles/beacon/compare/vv1.3.1...vv1.3.2) (2026-02-12)
### Bug Fixes

* Hotfix: Fixed commands registry crashing and failing to load the bot while trying to handle command groups. ([dd8bfb0](https://github.com/likerofturtles/beacon/commit/dd8bfb0280cf9aea43f7997f1e27529b8f2e2f5c))

## [v1.3.1](https://github.com/likerofturtles/beacon/compare/vv1.3.0...vv1.3.1) (2026-02-12)
### Bug Fixes

* Added relative import fix in dashboard.py to fix this error that occurs when attempting to load internal cog: ERROR: Failed to start the bot: Extension 'beacon.ext.diagnostics' raised an error: ModuleNotFoundError: No module named 'src' ([3cbc6d9](https://github.com/likerofturtles/beacon/commit/3cbc6d94dcca6e155473a18c5521aa95ce1e2bcf))

## [v1.3.0](https://github.com/likerofturtles/beacon/compare/vv1.2.4...vv1.3.0) (2026-02-12)
### Features & Minor Updates and Changes

* Added ephemeral option to /od command that shows the owners dashboard. The dashboard is now sent as non-ephemeral by default, but you can choose to make it ephemeral using the option. ([defa142](https://github.com/likerofturtles/beacon/commit/defa142f3f6eef6c7d6853b21ff998317ca96e54))

### Bug Fixes

* Added relative import to fix this error that occurs when attempting to load internal cog: ERROR: Failed to start the bot: Extension 'beacon.ext.diagnostics' raised an error: ModuleNotFoundError: No module named 'src' ([0f29ed1](https://github.com/likerofturtles/beacon/commit/0f29ed13332724e4a6f1ebfa968a6ae2a072030e))

### Styling, UI, Code Cleanup, and Linting Fixes

* Added "Beacon: " prefix to all strings and to owner dashboard header. Because, branding is always nice! ([83a6e29](https://github.com/likerofturtles/beacon/commit/83a6e299a082fa46d6b687cb50f11880fd3cda5d))

### Documentation Changes

* Updated README. ([c2b080b](https://github.com/likerofturtles/beacon/commit/c2b080b46e1aa8188962adf813fe9df440a59416))

## [v1.2.4](https://github.com/likerofturtles/beacon/compare/vv1.2.3...vv1.2.4) (2026-02-12)
### Bug Fixes

* Fixed capitalization of Bot in legacy support import statement. Legacy support now works perfectly. ([1651b9f](https://github.com/likerofturtles/beacon/commit/1651b9f9bb4602916051bfb07e53f3f85692c0e0))

## [v1.2.3](https://github.com/likerofturtles/beacon/compare/vv1.2.2...vv1.2.3) (2026-02-12)
### Bug Fixes

* Fixed legacy support. Before: beacon.py in root folder. This wasn't being included in the package when it was being built. Now: beacon directory with __init__.py with the same code. Legacy support now works. ([2fa0ee5](https://github.com/likerofturtles/beacon/commit/2fa0ee54cab7020ecef623d9c02769c40b45c991))

### Documentation Changes

* Expanded intro in readme: "In technical terms, this is a **Flexible Boilerplate Framework**." ([0ad11b7](https://github.com/likerofturtles/beacon/commit/0ad11b7c570690d1c6e5082cd7c19566245ef4ab))

## [v1.2.2](https://github.com/likerofturtles/beacon/compare/vv1.2.1...vv1.2.2) (2026-02-12)
### Bug Fixes

* Added "v" prefix to internal cog framework version. ([a477468](https://github.com/likerofturtles/beacon/commit/a4774686798a0766ef37162d74235c29dc5c36dc))
* Added "v" prefix to print and log statements in bot.py. ([ee8ad77](https://github.com/likerofturtles/beacon/commit/ee8ad7709871d52b7756b2079824763f7c71b257))

## [v1.2.1](https://github.com/likerofturtles/beacon/compare/vv1.2.0...vv1.2.1) (2026-02-12)
### Bug Fixes

* Fixed internal cog's version not updating on version bump. ([5683fe1](https://github.com/likerofturtles/beacon/commit/5683fe1203f7bacdcb3c9ff6677bad8d9174430f))

## [v1.2.0](https://github.com/likerofturtles/beacon/compare/vv1.1.1...vv1.2.0) (2026-02-12)
### Features

* Renamed folder from beacon to beacon. Now, use "from beacon import ..." for imports instead of beacon. (Note: This isn't a breaking change, because you can still use beacon and it will automatically import from "beacon". However, this legacy support will be dropped in the next major release, so it's highly recommended to use "beacon" in your code. ([0559afe](https://github.com/likerofturtles/beacon/commit/0559afee7a7ec77fc8ab1f04d4038f7f17fef41e))

### Styling, UI, Code Cleanup, and Linting Fixes

* Updated colours for in-built cog's graph and embed. ([72b9e3b](https://github.com/likerofturtles/beacon/commit/72b9e3be45a0c366a84dd4bbfbc72912603e75f8))

### Documentation Changes

* Updated code snippets in readme to use the new "beacon" name in imports. ([8503cae](https://github.com/likerofturtles/beacon/commit/8503cae20cafa4ec1c54e37f22bca889d450660f))
* updated readme. ([cc28971](https://github.com/likerofturtles/beacon/commit/cc289715b118731a0721443456d7cdd7ea5626fc))

## [v1.1.1](https://github.com/likerofturtles/beacon/compare/v1.1.0...v1.1.1) (2026-02-12)


### Bug Fixes

* sync callbacks now use the return statement so that errors can be shown (if any) instead of hard-coded success response. ([e85b752](https://github.com/likerofturtles/beacon/commit/e85b752643fe94ec0fedf3e194d57d4dfcf26814))
