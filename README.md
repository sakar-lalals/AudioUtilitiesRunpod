# AudioUtilitiesRunpod

# Testing Audio To Midi
docker build -f Dockerfile.AudioToMidiConverter.test -t audiotomidi .
docker run audiotomidi

# Audio To Midi Runpod 
docker build --platform linux/amd64 -f Dockerfile.AudioToMidiConverter -t audiotomidiconverter .
docker tag audiotomidiconverter:latest sakarlalals/audiotomidiconverter:latest
docker push sakarlalals/audiotomidiconverter:latest

