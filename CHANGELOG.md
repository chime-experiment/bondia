# [0.4.0](https://github.com/chime-experiment/bondia/compare/v0.3.0...v0.4.0) (2020-12-03)


### Bug Fixes

* **auth:** logout ([0d451f0](https://github.com/chime-experiment/bondia/commit/0d451f0d37fe00478e677e87b6259d1c73a92615)), closes [#87](https://github.com/chime-experiment/bondia/issues/87)
* **data:** free least recently used files ([9b369ec](https://github.com/chime-experiment/bondia/commit/9b369ec91c52c81c536973a72b2363f6edeefae9))
* **sensitivity:** don't mod ra index before imshow_sections ([a4ccf38](https://github.com/chime-experiment/bondia/commit/a4ccf384558c02a40b6d7d1e7fe6dcf415f11d72))


### Features

* **gui:** add info tables ([ccb45d5](https://github.com/chime-experiment/bondia/commit/ccb45d54baafa4cdf3bd56dbdbabb6e38e184622)), closes [#84](https://github.com/chime-experiment/bondia/issues/84) [#85](https://github.com/chime-experiment/bondia/issues/85)
* **gui:** require note if decision is bad ([5b6a858](https://github.com/chime-experiment/bondia/commit/5b6a8583537c5ae9d8d321244e9837813795bfca)), closes [#81](https://github.com/chime-experiment/bondia/issues/81)
* **plot:** parameterize height ([9ac8d65](https://github.com/chime-experiment/bondia/commit/9ac8d65874ed5d2f3a94adc140fd8941ecde743d))
* **ringmap:** add option intercylinder_only ([9b01bb1](https://github.com/chime-experiment/bondia/commit/9b01bb1c5488edaa500abee668cc38000c3e6408)), closes [#80](https://github.com/chime-experiment/bondia/issues/80)
* **ringmap:** set bgcolor to lightgray ([79899e9](https://github.com/chime-experiment/bondia/commit/79899e9ed6634472f8cc6d0ff1e966108392e486))
* **sensitivity:** add flag filter ([4fdad34](https://github.com/chime-experiment/bondia/commit/4fdad342fce40089e3c703a06e9ad40909a3f918)), closes [#86](https://github.com/chime-experiment/bondia/issues/86)
* **sensitivity:** add option: divide by estimate ([9feb3c3](https://github.com/chime-experiment/bondia/commit/9feb3c39d3a245da23d438b9fbfc56a0a8629b62)), closes [#79](https://github.com/chime-experiment/bondia/issues/79)
* **gui:** show notes of other users ([303b480](https://github.com/chime-experiment/bondia/commit/303b480b0600bd7d261c6f7b829cf18259e711c2))



# [0.3.0](https://github.com/chime-experiment/bondia/compare/v0.2.0...v0.3.0) (2020-11-04)


### Bug Fixes

* **data:** don't accept days with missing plots ([6b4458a](https://github.com/chime-experiment/bondia/commit/6b4458a986bea16dfc2852f961d28519bb69031a)), closes [#63](https://github.com/chime-experiment/bondia/issues/63)
* **data:** raise DataError if file not found ([80dcbd5](https://github.com/chime-experiment/bondia/commit/80dcbd5d116cff02587e9e351f9449ede1913d88))
* **data:** raise DataError if trying to load nonexistant data ([f1cc484](https://github.com/chime-experiment/bondia/commit/f1cc4846a3ae571036d08eddc862a3465c5c260a))
* **data:** Skip non-lsd dirs ([29b046e](https://github.com/chime-experiment/bondia/commit/29b046e539bb72c3bf8ca1dde01bead924a7ad44))
* **data:** typo in debug log ([ecf17ec](https://github.com/chime-experiment/bondia/commit/ecf17ecc70f01faad75f1b5a285cfea7f19ab96a))
* **delayspectrum:** copy cmap to get rid of mpl warning ([e812e49](https://github.com/chime-experiment/bondia/commit/e812e49bb1d7a1015c54865c9e6b9206d77469ef))
* **delayspectrum:** swap axis names when transposing ([d63fc94](https://github.com/chime-experiment/bondia/commit/d63fc94779420922d85f8fe07e5e4f44353f770e))
* **gui:** get user name from secure cookie ([33044f8](https://github.com/chime-experiment/bondia/commit/33044f8a1b28be9266d51d82c64e738e5b986597)), closes [#37](https://github.com/chime-experiment/bondia/issues/37)
* **gui:** no day value set on start ([87db63d](https://github.com/chime-experiment/bondia/commit/87db63de4b71993c3190f7e60088cc08c84a0107))
* **gui:** plot order in set gets scrambled ([be956e4](https://github.com/chime-experiment/bondia/commit/be956e447cae55289ec7c11ef4cf8f489e99295e))
* **gui:** Toggle buttons were assigned to wrong plots ([3aeb40a](https://github.com/chime-experiment/bondia/commit/3aeb40ad0bcec9e3368412a1b1bbf3edc6da0304))
* **heatmap:** import datashade after start to make --num_procs work ([9669ead](https://github.com/chime-experiment/bondia/commit/9669ead3b4dfc417fd35978a2509323e99cfddc0))
* **heatmap:** set transpose default to False ([9e41195](https://github.com/chime-experiment/bondia/commit/9e4119510d221bfd4f47eb88a9675ee64f58256e)), closes [#57](https://github.com/chime-experiment/bondia/issues/57)
* **server:** load template after config ([75f03c8](https://github.com/chime-experiment/bondia/commit/75f03c8c449f0a4621bfd02f0cd3c482547362cb))
* **template:** Menu button wasn't displayed at all ([6d3ecae](https://github.com/chime-experiment/bondia/commit/6d3ecaea48ed38822748b9851e73e2f810b1b1f6))


### Features

* **config:** add logging config ([1aa53ef](https://github.com/chime-experiment/bondia/commit/1aa53efd997d83f35847fb0bd5212db71b48b36a))
* **data:** periodically re-index files ([5470e1a](https://github.com/chime-experiment/bondia/commit/5470e1a9be39245c4864dd64756bd1bbbcd75313)), closes [#24](https://github.com/chime-experiment/bondia/issues/24)
* **delayspectrum:** arrange plots in single row ([727f254](https://github.com/chime-experiment/bondia/commit/727f2546465c66869e5677fb46d9b5395a34408e)), closes [#34](https://github.com/chime-experiment/bondia/issues/34)
* **delayspectrum:** make axes of subplots independent ([4b8c327](https://github.com/chime-experiment/bondia/commit/4b8c3273af2649e012de9d3eee77bcb4bce81b5e))
* **delayspectrum:** optimize plot layout ([d06e17c](https://github.com/chime-experiment/bondia/commit/d06e17cab33f549694abdad3b9e77a1c1b48b454))
* **flags:** default uncached flag fetching ([7d0a3ac](https://github.com/chime-experiment/bondia/commit/7d0a3ac6b79937752c4ae7cff221bfd97e47d2a1))
* **gui:** add indicator for when page loading ([15264b5](https://github.com/chime-experiment/bondia/commit/15264b5b80c921c633132fa8007004fb89f82b33)), closes [#65](https://github.com/chime-experiment/bondia/issues/65)
* **gui:** add option to hide days with opinion ([3935db4](https://github.com/chime-experiment/bondia/commit/3935db4bf8489dcbaa62df0b93c0a720e5c1745f)), closes [#65](https://github.com/chime-experiment/bondia/issues/65)
* **gui:** describe displayed data in a title ([84a87d9](https://github.com/chime-experiment/bondia/commit/84a87d9002304010e30683a46be7e640635079c6)), closes [#33](https://github.com/chime-experiment/bondia/issues/33)
* **gui:** opinion buttons insert into chimedb ([1f92c75](https://github.com/chime-experiment/bondia/commit/1f92c75b58ef05f95e70a3ff7902331aff0073cf))
* **gui:** swap plot order to fit them tighter ([b3437be](https://github.com/chime-experiment/bondia/commit/b3437be14deb2bd24c182f1f21e088df6577931d))
* **gui:** use alert widget to give opinion click feedback ([a91bf3b](https://github.com/chime-experiment/bondia/commit/a91bf3b0646e2443a51f18b767ad53dc78bb8c83))
* **opinion:** add notes text input ([f841c55](https://github.com/chime-experiment/bondia/commit/f841c5548a6ef0b6b69c31a116d6dbcf412849d7)), closes [#64](https://github.com/chime-experiment/bondia/issues/64)
* **opinion:** choose next day closeby after opinion inserted ([f099f5b](https://github.com/chime-experiment/bondia/commit/f099f5bcf1e7f67db112ecc3c7b9a3f36337ffd8)), closes [#62](https://github.com/chime-experiment/bondia/issues/62)
* **plot:** pass config to plot ([174c536](https://github.com/chime-experiment/bondia/commit/174c5366bc44f51e5a9a2356a45660e6b29ab520))
* **requirements:** bump bokeh version to 2.2.1 ([57848eb](https://github.com/chime-experiment/bondia/commit/57848eb96adac05a02bbf75f81712975cb56a074))
* **ringmap:** add ringmap plot ([97e19cf](https://github.com/chime-experiment/bondia/commit/97e19cf8e392a224902ecde6b39cbc1e303a70aa))
* **script:** add option --chimedb-enable-test ([4b28836](https://github.com/chime-experiment/bondia/commit/4b28836b73721f7c4217ebac34e23bdb13c7a537))
* **sensitivity:** Add sensitivity plot ([67402cb](https://github.com/chime-experiment/bondia/commit/67402cb7f1d254d4d2c05a6911a18b65c640d27a))
* **template:** add mdl w/o tabs ([d5365f5](https://github.com/chime-experiment/bondia/commit/d5365f56dfd3562e4ab3ee7b9c910e5c3ae138de))
* **templates:** add template mdl ([28cad5e](https://github.com/chime-experiment/bondia/commit/28cad5e73458f7bc8e5036a36e78152d10092cdb))


### Performance Improvements

* **server:** open db connection on startup ([4e648c6](https://github.com/chime-experiment/bondia/commit/4e648c68e98b7160a98c302386d9b56845b69adb))



### [0.2.0]  (2020-07-23)


### Bug Fixes

* **delayspectrum:** ignore broken spectra ([eeeeac8](https://github.com/chime-experiment/bondia/commit/eeeeac8c4abad2a860b9faf036eae98664b74af5)), closes [#23](https://github.com/chime-experiment/bondia/issues/23)
* **plot:** hide expandbutton after de/activate plot ([fc339c9](https://github.com/chime-experiment/bondia/commit/fc339c9c5c7a9544aa19e9bb85a8f69e9b546b22))


### Features

* **data:** data revisions ([c842391](https://github.com/chime-experiment/bondia/commit/c8423910d58976650a914b20d5b9e0129e9f82d7))
* **script:** user authentication ([5da4ff4](https://github.com/chime-experiment/bondia/commit/5da4ff4499790359fee94f7662c7471857e78b90)), closes [#2](https://github.com/chime-experiment/bondia/issues/2)
* **template:** add link to github repo ([d8dc0b0](https://github.com/chime-experiment/bondia/commit/d8dc0b0e8dda598bc1dbf289898e942d793e6683))
* **template:** turn on drawer shadow ([045a2bd](https://github.com/chime-experiment/bondia/commit/045a2bd058cfe608e9dc3c9f84eaa8c0876ea176))



### [0.1.0] (2020-06-25)

First tagged version.

### Bug Fixes

* **delayspectrum:** always show colormap ([ece43c0](https://github.com/chime-experiment/bondia/commit/ece43c0d07649a505472b2c8bab5e229bad5a031)), closes [#11](https://github.com/chime-experiment/bondia/issues/11)
* **delayspectrum:** set min width ([6893e2b](https://github.com/chime-experiment/bondia/commit/6893e2bf43f48b3398392fb4e784d02a9b391c52)), closes [#19](https://github.com/chime-experiment/bondia/issues/19)
* **script:** pass function to panel.serve ([cecaa94](https://github.com/chime-experiment/bondia/commit/cecaa94c242e261e1d0f6f96cfdd68e4edbf423a))
* **template:** reduce width of menu items ([6b68f29](https://github.com/chime-experiment/bondia/commit/6b68f29190484fed0a74f7c87718600648d46adf))


### Features

* **delayspectrum:** give user control over datashade function ([f4e2233](https://github.com/chime-experiment/bondia/commit/f4e22330b5b50453e81a1027279b9ab41a266a8f))
* **gui:** Link day selector to plots ([9ccb20f](https://github.com/chime-experiment/bondia/commit/9ccb20f4dfdcd4d52ace11c20f06e47b776bbd25))
* **plot:** autosize plots ([66d357f](https://github.com/chime-experiment/bondia/commit/66d357fe8c90bbd971d8661206436c232dbffa33))
* **script:** add option --websocket_origin ([8a32b69](https://github.com/chime-experiment/bondia/commit/8a32b6920c9d3f75faf0e05f27e6dadf65d353e9))
* **scripts:** panel serve ([a4552a7](https://github.com/chime-experiment/bondia/commit/a4552a79e584ab32f40e1d1fd911c9948266e2a8))
* **template:** set drawer mode=modal ([b01ba7d](https://github.com/chime-experiment/bondia/commit/b01ba7d93c4238220096374e22f45a3286000d6f))
* **template:** start with drawer menu closed ([798fa5e](https://github.com/chime-experiment/bondia/commit/798fa5e3bd62d1a74f0f3e36ca7b85470571aaf2))



