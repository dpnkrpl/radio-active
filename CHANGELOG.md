## 4.1.1

1. Dynamic ASCII audio spectrum visualizer in Zen mode 🧘✨

## 4.1.0

1. Significant improvements on app loading speed :zap:
2. Recording quality improved 🎶
3. Added recording library command `rl` which allows you to play, delete, rename and shazam your recordings
4. Faster station lookup
5. Fix playback issues with ffplay
6. Optimize interaction with external player, improving play/pause time
7. Improved fuzzy find logic 🔍
8. Stability improvements for windows
9. Critical bug fixes 🐛
10. Minor UI fixes

## 4.0.3

1. Fix broken installation on python >=3.13
2. NOTE: shazam does not work anymore on python version >= 3.13


## 4.0.2

1. More information on the shazam identified track
2. Minor UI improvements

## 4.0.1

1. Fix broken install on windows
2. Fix recording issues on windows

## 4.0.0

1. Shazam !! song identification built-in 🚀
2. Auto fetch current track information and send desktop notification
3. Volume control
4. Major UI changes
5. Command prompt with advanced tab completion 🚀
6. Real-time fuzzy station search across favorites and history
7. Interactive station selection menu via `l/list` command
8. Improved help menu and recording UI
9. Zen mode
10. Background play
11. Stability improvements

## 3.0.4

1. Release notes are now shown to the end users for future versions

## 3.0.3

1. Minor improvements and bug fixes

## 3.0.2

1. Fix pkg_resources package error on latest python versions

## 3.0.1

1. Minor stability improvements

## 3.0.0

1. Sleep Timer and configuration updates
2. Minimal Mode and Info Runtime Command
3. Implement compile-time feature configuration system
4. Add runtime search and cycle commands
5. Implement alias management, configuration handling, last station persistence, and XDG-compliant path management.
6. Other improvements

## 2.9.1

1. Play a random station from favorite list `--random`
2. Multiple media player support ( MPV, VLC, FFplay) `--player`
3. Filter search results with `--filter`
4. Play/Pause player from runtime command `p`
5. Default config file support added
6. Fixed minor bugs while giving runtime commands


## 2.9.0

1. Fetch current playing track info from runtime commands 🎶 ⚡
2. Sort results with several parameters like: click-count, popularity, bitrate, random etc. `--sort`
3. Select stations from favorite menu to remove them `--remove`
4. Result page will adjust width according to the actual terminal window size
5. Squashed CTRL+D unhandled bugs
6. Detect station name while playing with direct url
7. Play a random station from result page
8. See station information from runtime command

## 2.8.0

1. Selection menu added for `--country` and `--tag` results. Play directly from result page.
2. `ffplay` and `ffmpeg` will show debug info while started with `--loglevel debug`
3. Autodetect the codec information and set the file extension of the recorded file.
4. Force a recording to be in mp3 format only.
5. Simpler command help message


## 2.7.0

1. Recording support added 🎉 . save recording as mp3 or wav 🎶 `--record`
2. Play a station from your favorite list or stream a URL directly without any user selection menu. Useful when running from other scripts. `--play`
3. Play the last played station directly. `--last`
4. Runtime command feature added. Perform actions on demand ⚡
5. A caching mechanism was added for fewer API calls. Faster radio playbacks!
6. Code refactored. It is easier for contributors to implement new features.
7. BREAKING CHANGES: `--station` -> `--search`, `--discover-by-country` -> `--country`, `--discover-by-tag` -> `--tag`, `--discover-by-state` -> `--state`, `--discover-by-language` -> `--language`, `--add-station` -> `--add`, `--add-to-favorite` -> `--favorite`, `--show-favorite-list` -> `--list`


## 2.6.0

1. Detect errors while trying to play a dead station or encountering other connection errors.
2. Playing a station will increase the click (vote) counter for that station on the server.
3. Fixed bugs that occurred when there was a blank entry in the favorite station file.
4. Fixed bugs that caused empty last stations.
5. Handled errors related to connection issues when attempting to search for a station.
6. Improved `ffplay` process handling by introducing a thread to monitor runtime errors from the process.
7. `pyradios` module updated to latest version.


## 2.5.2

1. Added `--kill` option to stop background radios if any.
2. Project restructured.
3. Fixed saving empty last station information.



## 2.5.1

1. Fixed RuntimeError with empty selection menu on no options provided to radio.
2. Display the current station name as a panel while starting the radio with `--uuid`
3. Minor typos were fixed in the help message.
4. Station names do not contain any unnecessary spaces now
5. Do not play any stations while `--flush` is given. Just delete the list and exit.

## 2.5.0

1. Added a selection menu while no station information is provided. This will include the last played station and the favorite list.
2. Added `--volume` option to the player. Now you can pass the volume level to the player.
3. `ffplay` initialization errors handled. Better logic to stop the PID of `ffplay`
4. Some unhandled errors are now handled
5. Minor typos fixed
6. `sentry-sdk` added to gater errors (will be removed on next major release)
7. About section updated to show donation link
8. The upgrade message will now point to this changelog file
9. Updated documentation

## 2.4.0

1. Crashes on Windows fixed
2. Fixed setup-related issues (development purpose)

## 2.3.0

1. Discover stations by country
2. Discover stations by state
3. Discover stations by genre/tags
4. Discover stations by language
5. More info on multiple results for a station name
6. Shows currently playing radio info as box
7. sentry-SDK removed
8. Help table improved
9. Other minor bugs fixed

## 2.2.0

1. Pretty Print welcome message using Rich
2. More user-friendly and gorgeous
3. Added several new options `-F`,`-W`,`-A`,`--flush`
4. Fixed unhandled Exception when trying to quit within 3 seconds
5. Supports User-Added stations
6. Alias file now supports both UUID and URL entry
7. Fixed bugs in playing last station (which is actually an alias under fav list)
8. New Table formatted help message
9. Notification for new app version
10. Several typos fixed
11. Asciinema demo added
12. README formatted
13. Pylint the codebase
14. Added support section
15. python imports Sorted
16. Alias pattern updated from `=` to `==`
17. Many more

## 2.1.3

1. Fixed bugs in the last station
2. Typos fixed
3. Formatted codebase
4. Logging issued fixed
5. Sentry Added to collect unhandled Exceptions logs only


## 2.1.2

1. Updated README and project details
2. Fixed minor bugs

## 2.1.1

1. Minor bugs fixed
2. Station aliasing support

## 2.1.0

1. Minor bugs quashed

## 2.0.4

1. Initial release
