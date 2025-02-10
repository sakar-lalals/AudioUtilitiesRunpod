# AudioUtilitiesRunpod

# Testing Audio To Midi
docker build -f Dockerfile.AudioToMidiConverter.test -t audiotomidi .
docker run audiotomidi

# Audio To Midi Runpod 
docker build --platform linux/amd64 -f Dockerfile.AudioToMidiConverter -t audiotomidiconverter .
docker tag audiotomidiconverter:latest sakarlalals/audiotomidiconverter:latest
docker push sakarlalals/audiotomidiconverter:latest

# Audio Utilities test
docker build -f Dockerfile.AudioUtilities.test -t lalals-audio-utilities-test .
docker run -v ./audio_separator_weights:/runpod_volume/audio-separator-models -v ./output:/tmp/outputs lalals-audio-utilities-test



# Audio Utilities GPU
docker build --platform "linux/amd64" -f Dockerfile.AudioUtilities.gpu -t lalals-audio-utilities .
docker tag lalals-audio-utilities:latest sakarlalals/lalals-audio-utilities:latest
docker push sakarlalals/lalals-audio-utilities:latest


# Audio Downloader Test 
docker build -f YoutubeDownloader/Dockerfile.test -t lalals-audio-downloader-test . 
docker run lalals-audio-downloader-test

# Audio Downloader Runpod 
docker build --platform "linux/amd64" -f YoutubeDownloader/Dockerfile -t lalals-audio-downloader .
docker tag lalals-audio-downloader:latest sakarlalals/lalals-audio-downloader:0.2
docker push sakarlalals/lalals-audio-downloader:0.2