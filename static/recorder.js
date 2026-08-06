// AudioWorklet processor — converts float32 mic samples to 16-bit PCM bytes
class Recorder extends AudioWorkletProcessor {
  process(inputs) {
    const input = inputs[0][0];
    if (!input) return true;

    // Convert Float32 [-1, 1] to Int16
    const pcm = new Int16Array(input.length);
    for (let i = 0; i < input.length; i++) {
      pcm[i] = Math.max(-32768, Math.min(32767, input[i] * 32768));
    }

    this.port.postMessage(pcm.buffer, [pcm.buffer]);
    return true;
  }
}

registerProcessor("recorder", Recorder);
