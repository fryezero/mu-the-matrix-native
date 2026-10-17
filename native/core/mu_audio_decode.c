/* Platform decoder for the compressed music and ambience files (MP3, Ogg
 * Vorbis). On macOS this is AudioToolbox's ExtAudioFile, decoding offline to
 * interleaved float at the file's own rate and channel count. Other
 * platforms report the codec as unavailable; WAV needs no platform decoder. */
#include "mu_audio.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#if defined(__APPLE__) && !defined(MU_NO_AUDIOTOOLBOX)
#include <AudioToolbox/AudioToolbox.h>

int mu_audio_decode_platform(const char *host_path, mu_pcm *out, char *error, size_t error_size)
{
    memset(out, 0, sizeof *out);
    CFURLRef url = CFURLCreateFromFileSystemRepresentation(NULL, (const UInt8 *)host_path,
                                                           (CFIndex)strlen(host_path), false);
    if (!url) {
        snprintf(error, error_size, "bad path %s", host_path);
        return -1;
    }
    ExtAudioFileRef file = NULL;
    OSStatus status = ExtAudioFileOpenURL(url, &file);
    CFRelease(url);
    if (status != noErr || !file) {
        snprintf(error, error_size, "AudioToolbox cannot open %s (%d)", host_path, (int)status);
        return -1;
    }
    AudioStreamBasicDescription source;
    UInt32 size = sizeof source;
    status = ExtAudioFileGetProperty(file, kExtAudioFileProperty_FileDataFormat, &size, &source);
    SInt64 length = 0;
    UInt32 length_size = sizeof length;
    if (status == noErr)
        status = ExtAudioFileGetProperty(file, kExtAudioFileProperty_FileLengthFrames, &length_size, &length);
    if (status != noErr || source.mChannelsPerFrame == 0 || source.mChannelsPerFrame > 8 || source.mSampleRate <= 0) {
        ExtAudioFileDispose(file);
        snprintf(error, error_size, "unsupported stream in %s", host_path);
        return -1;
    }
    AudioStreamBasicDescription client = {0};
    client.mSampleRate = source.mSampleRate;
    client.mFormatID = kAudioFormatLinearPCM;
    client.mFormatFlags = kAudioFormatFlagIsFloat | kAudioFormatFlagIsPacked;
    client.mChannelsPerFrame = source.mChannelsPerFrame;
    client.mBitsPerChannel = 32;
    client.mFramesPerPacket = 1;
    client.mBytesPerFrame = 4*source.mChannelsPerFrame;
    client.mBytesPerPacket = client.mBytesPerFrame;
    status = ExtAudioFileSetProperty(file, kExtAudioFileProperty_ClientDataFormat, sizeof client, &client);
    if (status != noErr) {
        ExtAudioFileDispose(file);
        snprintf(error, error_size, "cannot convert %s (%d)", host_path, (int)status);
        return -1;
    }
    size_t capacity = length > 0 ? (size_t)length + 4096 : 1u << 20;
    size_t frames = 0;
    float *samples = malloc(capacity*client.mChannelsPerFrame*sizeof(float));
    while (samples) {
        if (frames + 4096 > capacity) {
            capacity *= 2;
            float *grown = realloc(samples, capacity*client.mChannelsPerFrame*sizeof(float));
            if (!grown) { free(samples); samples = NULL; break; }
            samples = grown;
        }
        AudioBufferList list;
        list.mNumberBuffers = 1;
        list.mBuffers[0].mNumberChannels = client.mChannelsPerFrame;
        list.mBuffers[0].mDataByteSize = (UInt32)(4096*client.mBytesPerFrame);
        list.mBuffers[0].mData = samples + frames*client.mChannelsPerFrame;
        UInt32 count = 4096;
        status = ExtAudioFileRead(file, &count, &list);
        if (status != noErr) { free(samples); samples = NULL; break; }
        if (count == 0) break;
        frames += count;
    }
    ExtAudioFileDispose(file);
    if (!samples || frames > 0xffffffffu) {
        snprintf(error, error_size, "decode failed for %s (%d)", host_path, (int)status);
        return -1;
    }
    out->samples = samples;
    out->frames = (uint32_t)frames;
    out->channels = (uint16_t)client.mChannelsPerFrame;
    out->rate = (uint32_t)(source.mSampleRate + 0.5);
    out->format = 0;
    out->bits = 32;
    return 0;
}
#else
int mu_audio_decode_platform(const char *host_path, mu_pcm *out, char *error, size_t error_size)
{
    memset(out, 0, sizeof *out);
    snprintf(error, error_size, "no platform decoder for %s (MP3/OGG need macOS AudioToolbox)", host_path);
    return -1;
}
#endif
