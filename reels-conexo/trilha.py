# Gera a trilha original do Reels (16 s, 120 BPM), sincronizada com as cenas
# do index.html. Tudo é sintetizado aqui, sem samples externos.
# Uso: python3 trilha.py  → trilha.wav
import os
import wave
import numpy as np

SR = 44100
DUR = 16.0
BPM = 120
BEAT = 60 / BPM          # 0,5 s; um compasso = 2 s
N = int(SR * DUR)
rng = np.random.default_rng(7)
t_all = np.arange(N) / SR

# cortes de cena no index.html
CORTES = [3.2, 6.6, 10.2, 13.0]


def hz(nota):
    return 440.0 * 2 ** ((nota - 69) / 12)


def lowpass(x, corte):
    """Passa-baixas suave aplicado no domínio da frequência."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1 / np.sqrt(1 + (f / corte) ** 4)
    return np.fft.irfft(X, len(x))


def bandpass(x, centro, largura):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= np.exp(-0.5 * ((f - centro) / largura) ** 2)
    return np.fft.irfft(X, len(x))


def put(buf, sinal, inicio):
    i = int(inicio * SR)
    if i >= len(buf):
        return
    j = min(len(buf), i + len(sinal))
    buf[i:j] += sinal[: j - i]


L = np.zeros(N)
R = np.zeros(N)


def put_st(sinal, inicio, pan=0.0, ganho=1.0):
    put(L, sinal * ganho * np.sqrt(0.5 * (1 - pan)), inicio)
    put(R, sinal * ganho * np.sqrt(0.5 * (1 + pan)), inicio)


# progressão: Am – F – C – G (vi–IV–I–V), um acorde por compasso
ACORDES = [
    [57, 60, 64],  # Am
    [53, 57, 60],  # F
    [48, 55, 60, 64],  # C
    [55, 59, 62],  # G
]
BAIXO = [45, 41, 48, 43]


def acorde(c):
    return ACORDES[int(c) % 4]


# ---------- pad (supersaw filtrado, entra suave) ----------
for c in range(8):
    ini = c * 2.0
    d = 2.0
    tt = np.arange(int(d * SR)) / SR
    env = np.minimum(1, tt / 0.25) * np.minimum(1, (d - tt) / 0.15 + 0.0)
    env = np.clip(env, 0, 1)
    for k, n in enumerate(acorde(c)):
        for det, pan in ((-0.12, -0.6), (0.0, 0.0), (0.12, 0.6)):
            f = hz(n + 12) * (1 + det / 100 * 2)
            saw = 2 * ((tt * f + rng.random()) % 1) - 1
            put_st(saw * env * 0.026, ini, pan)
L = lowpass(L, 2200)
R = lowpass(R, 2200)


# ---------- arpejo "pluck" em semicolcheias ----------
def pluck(f, d=0.35):
    tt = np.arange(int(d * SR)) / SR
    s = np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(2 * np.pi * 2 * f * tt) + 0.12 * np.sin(2 * np.pi * 3 * f * tt)
    return s * np.exp(-tt * 14)


padrao = [0, 1, 2, 1, 2, 0, 1, 2]
for c in range(8):
    notas = acorde(c)
    for i in range(16):  # 16 semicolcheias por compasso
        t0 = c * 2.0 + i * BEAT / 4
        if 12.8 <= t0 < 13.0:  # respiro antes do CTA
            continue
        n = notas[padrao[i % 8] % len(notas)] + 24
        ganho = 0.15 if i % 4 == 0 else 0.10
        if t0 < 2.0:
            ganho *= np.clip(t0 / 2.0, 0.6, 1)  # entra crescendo na abertura
        put_st(pluck(hz(n)), t0, pan=0.35 if i % 2 else -0.35, ganho=ganho)


# ---------- baixo (colcheias, a partir do 2º compasso) ----------
def baixo(f, d):
    tt = np.arange(int(d * SR)) / SR
    s = np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * 2 * f * tt)
    return s * np.minimum(1, tt / 0.005) * np.exp(-tt * 5)


for c in range(1, 8):
    for i in range(8):
        t0 = c * 2.0 + i * BEAT / 2
        if 12.8 <= t0 < 13.0:
            continue
        put_st(baixo(hz(BAIXO[c % 4]), BEAT / 2 * 0.95), t0, ganho=0.18 if i % 2 else 0.22)


# ---------- bateria ----------
def kick():
    d = 0.35
    tt = np.arange(int(d * SR)) / SR
    f = 50 + 110 * np.exp(-tt * 30)
    fase = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(fase) * np.exp(-tt * 9)


def hat(d=0.06):
    s = rng.standard_normal(int(d * SR))
    s = s - lowpass(s, 7000)
    return s * np.exp(-np.arange(len(s)) / SR * 60)


def clap():
    d = 0.25
    s = bandpass(rng.standard_normal(int(d * SR)), 1500, 700)
    tt = np.arange(len(s)) / SR
    env = np.exp(-tt * 18)
    for k in (0.0, 0.012, 0.024):  # "palmas" em camadas
        env += 0.6 * np.exp(-np.maximum(tt - k, 0) * 120) * (tt >= k)
    return s * env


K, H, C = kick(), hat(), clap()
for b in range(int(DUR / BEAT)):
    t0 = b * BEAT
    if t0 < 2.0 or 12.5 <= t0 < 13.0 or t0 >= 15.5:
        continue
    put_st(K, t0, ganho=0.36)
    put_st(H, t0 + BEAT / 2, pan=0.25, ganho=0.12)
    if b % 2 == 1 and t0 >= 4.0:
        put_st(C, t0, pan=-0.1, ganho=0.22)
    if t0 >= 10.0:  # hats extras para dar energia no final
        put_st(H, t0 + BEAT / 4, pan=-0.25, ganho=0.06)
        put_st(H, t0 + 3 * BEAT / 4, pan=0.25, ganho=0.06)

# virada de caixa antes do CTA
for i in range(8):
    put_st(C, 12.0 + i * BEAT / 8 * 2, ganho=0.08 + 0.02 * i)


# ---------- efeitos de transição ----------
def whoosh(d=0.6):
    n = int(d * SR)
    ruido = rng.standard_normal(n)
    tt = np.arange(n) / SR
    out = np.zeros(n)
    # varredura de grave para agudo em faixas com crossfade
    faixas = np.geomspace(300, 6000, 10)
    for k, fc in enumerate(faixas):
        centro = (k + 0.5) / len(faixas) * d
        janela = np.exp(-0.5 * ((tt - centro) / (d / len(faixas))) ** 2)
        out += bandpass(ruido, fc, fc * 0.4) * janela
    env = np.sin(np.pi * tt / d) ** 2
    return out * env / np.max(np.abs(out))


def brilho(t0, notas):
    """Sininhos do troféu."""
    for k, n in enumerate(notas):
        d = 1.6
        tt = np.arange(int(d * SR)) / SR
        f = hz(n)
        s = np.sin(2 * np.pi * f * tt) + 0.4 * np.sin(2 * np.pi * 2.76 * f * tt) * np.exp(-tt * 6)
        put_st(s * np.exp(-tt * 3), t0 + k * 0.07, pan=-0.5 + k * 0.33, ganho=0.06)


def impacto(t0):
    d = 1.4
    tt = np.arange(int(d * SR)) / SR
    f = 40 + 60 * np.exp(-tt * 12)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 3)
    s += lowpass(rng.standard_normal(len(tt)), 900) * np.exp(-tt * 6) * 0.6
    put_st(s, t0, ganho=0.5)


W = whoosh()
for corte in CORTES:
    put_st(W, corte - 0.45, pan=-0.3, ganho=0.10)
    put_st(W[::-1] * 0.5, corte - 0.45, pan=0.3, ganho=0.10)

brilho(3.45, [84, 88, 91, 96])   # troféu
impacto(0.1)                      # logo da abertura
impacto(13.05)                    # CTA

# acorde final sustentado
tt = np.arange(int(1.0 * SR)) / SR
for n in [48, 55, 60, 64, 67]:
    put_st(np.sin(2 * np.pi * hz(n + 12) * tt) * np.exp(-tt * 2.5), 15.0, ganho=0.05)

# ---------- master ----------
mix = np.stack([L, R], axis=1)
mix *= np.clip((DUR - t_all) / 0.6, 0, 1)[:, None]      # fade out
mix *= np.clip(t_all / 0.02, 0, 1)[:, None]             # sem clique no início
mix /= np.max(np.abs(mix)) + 1e-9
mix = np.tanh(mix * 1.6) / np.tanh(1.6) * 0.89          # limitador suave

saida = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trilha.wav")
with wave.open(saida, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
print("Trilha gerada:", saida)
