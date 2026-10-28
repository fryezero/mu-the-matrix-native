/* AUDIO-002: ordered SND_Load calls, ids + source sites only. No client paths. */
void mu_audio_register_monster(int32_t type, int preloaded,
    void (*load)(void *, uint32_t, int32_t, int32_t, int32_t), void *ctx)
{
    if (preloaded || !load) return;
    switch (type) {
    case 0:
        load(ctx, 0x01812fbau, 210, 2, 1);
        load(ctx, 0x01812ffbu, 211, 2, 1);
        load(ctx, 0x0181303cu, 212, 2, 1);
        load(ctx, 0x0181307du, 213, 2, 1);
        load(ctx, 0x018130beu, 214, 2, 1);
        break;
    case 1:
        load(ctx, 0x01813145u, 215, 2, 1);
        load(ctx, 0x01813186u, 216, 2, 1);
        load(ctx, 0x018131c7u, 217, 2, 1);
        load(ctx, 0x01813208u, 218, 2, 1);
        load(ctx, 0x01813249u, 219, 2, 1);
        break;
    case 2:
        load(ctx, 0x018132d0u, 220, 2, 1);
        load(ctx, 0x01813311u, 221, 2, 1);
        load(ctx, 0x01813352u, 222, 2, 1);
        break;
    case 3:
        load(ctx, 0x01813444u, 225, 2, 1);
        load(ctx, 0x01813485u, 226, 2, 1);
        load(ctx, 0x018134c6u, 227, 2, 1);
        load(ctx, 0x01813507u, 228, 2, 1);
        load(ctx, 0x01813548u, 229, 2, 1);
        break;
    case 4:
        load(ctx, 0x01813620u, 230, 2, 1);
        load(ctx, 0x01813661u, 231, 2, 1);
        load(ctx, 0x018136a2u, 232, 2, 1);
        load(ctx, 0x018136e3u, 233, 2, 1);
        load(ctx, 0x01813724u, 234, 2, 1);
        break;
    case 5:
        load(ctx, 0x018137abu, 235, 2, 1);
        load(ctx, 0x018137ecu, 236, 2, 1);
        load(ctx, 0x0181382du, 237, 2, 1);
        load(ctx, 0x0181386eu, 238, 2, 1);
        load(ctx, 0x018138afu, 239, 2, 1);
        break;
    case 6:
        load(ctx, 0x01813936u, 240, 2, 1);
        load(ctx, 0x01813977u, 241, 2, 1);
        break;
    case 7:
        load(ctx, 0x01813aebu, 245, 2, 1);
        load(ctx, 0x01813b2cu, 246, 2, 1);
        load(ctx, 0x01813b6du, 247, 2, 1);
        load(ctx, 0x01813baeu, 248, 2, 1);
        load(ctx, 0x01813befu, 249, 2, 1);
        break;
    case 8:
        load(ctx, 0x018139e2u, 242, 2, 1);
        load(ctx, 0x01813a23u, 243, 2, 1);
        load(ctx, 0x01813a64u, 244, 2, 1);
        break;
    case 9:
        load(ctx, 0x018133d9u, 223, 2, 1);
        break;
    case 10:
        load(ctx, 0x01813c76u, 250, 2, 1);
        load(ctx, 0x01813cb7u, 251, 2, 1);
        load(ctx, 0x01813cf8u, 252, 2, 1);
        load(ctx, 0x01813d39u, 253, 2, 1);
        load(ctx, 0x01813d7au, 254, 2, 1);
        break;
    case 11:
        load(ctx, 0x01813e01u, 255, 2, 1);
        load(ctx, 0x01813e42u, 256, 2, 1);
        load(ctx, 0x01813e83u, 257, 2, 1);
        load(ctx, 0x01813ec4u, 258, 2, 1);
        load(ctx, 0x01813f05u, 259, 2, 1);
        break;
    case 12:
        load(ctx, 0x0181455bu, 278, 2, 1);
        load(ctx, 0x0181459cu, 279, 2, 1);
        load(ctx, 0x018145ddu, 280, 2, 1);
        load(ctx, 0x0181461eu, 281, 2, 1);
        break;
    case 13:
        load(ctx, 0x0181455bu, 278, 2, 1);
        load(ctx, 0x0181459cu, 279, 2, 1);
        load(ctx, 0x018145ddu, 280, 2, 1);
        load(ctx, 0x0181461eu, 281, 2, 1);
        break;
    case 14:
        load(ctx, 0x0181443bu, 275, 2, 1);
        load(ctx, 0x0181447cu, 276, 2, 1);
        load(ctx, 0x018144bdu, 277, 2, 1);
        break;
    case 15:
        load(ctx, 0x01813f8cu, 260, 2, 1);
        load(ctx, 0x01813fcdu, 261, 2, 1);
        load(ctx, 0x0181400eu, 262, 2, 1);
        break;
    case 16:
        load(ctx, 0x01814182u, 266, 2, 1);
        load(ctx, 0x018141c3u, 267, 2, 1);
        load(ctx, 0x01814204u, 268, 2, 1);
        load(ctx, 0x01814245u, 269, 2, 1);
        break;
    case 17:
        load(ctx, 0x01814095u, 263, 2, 1);
        load(ctx, 0x018140d6u, 264, 2, 1);
        load(ctx, 0x01814117u, 265, 2, 1);
        break;
    case 18:
        load(ctx, 0x018142b0u, 270, 2, 1);
        load(ctx, 0x018142f1u, 271, 2, 1);
        load(ctx, 0x01814332u, 272, 2, 1);
        load(ctx, 0x01814373u, 273, 2, 1);
        load(ctx, 0x018143b4u, 274, 2, 1);
        break;
    case 19:
        load(ctx, 0x018146d6u, 282, 2, 1);
        load(ctx, 0x01814717u, 283, 2, 1);
        load(ctx, 0x01814758u, 284, 2, 1);
        load(ctx, 0x01814799u, 285, 2, 1);
        load(ctx, 0x018147dau, 286, 2, 1);
        break;
    case 20:
        load(ctx, 0x01814861u, 287, 2, 1);
        load(ctx, 0x018148a2u, 288, 2, 1);
        load(ctx, 0x018148e3u, 289, 2, 1);
        load(ctx, 0x01814924u, 290, 2, 1);
        load(ctx, 0x01814965u, 291, 2, 1);
        break;
    case 21:
        load(ctx, 0x018149d0u, 292, 2, 1);
        load(ctx, 0x01814a11u, 293, 2, 1);
        load(ctx, 0x01814a52u, 294, 2, 1);
        break;
    case 22:
        load(ctx, 0x01814ad9u, 295, 2, 1);
        load(ctx, 0x01814b1au, 296, 2, 1);
        load(ctx, 0x01814b5bu, 297, 2, 1);
        load(ctx, 0x01814b9cu, 298, 2, 1);
        load(ctx, 0x01814bddu, 299, 2, 1);
        break;
    case 23:
        load(ctx, 0x01814c64u, 300, 2, 1);
        load(ctx, 0x01814ca5u, 301, 2, 1);
        load(ctx, 0x01814ce6u, 302, 2, 1);
        load(ctx, 0x01814d27u, 303, 2, 1);
        load(ctx, 0x01814d68u, 304, 2, 1);
        break;
    case 24:
        load(ctx, 0x01814defu, 305, 2, 1);
        load(ctx, 0x01814e30u, 306, 2, 1);
        load(ctx, 0x01814e71u, 307, 2, 1);
        load(ctx, 0x01814eb2u, 308, 2, 1);
        load(ctx, 0x01814ef3u, 309, 2, 1);
        break;
    case 25:
        load(ctx, 0x01814f7au, 310, 2, 1);
        load(ctx, 0x01814fbbu, 311, 2, 1);
        load(ctx, 0x01814ffcu, 312, 2, 1);
        load(ctx, 0x0181503du, 313, 2, 1);
        load(ctx, 0x0181507eu, 314, 2, 1);
        break;
    case 26:
        load(ctx, 0x01815105u, 315, 2, 1);
        load(ctx, 0x01815146u, 316, 2, 1);
        load(ctx, 0x01815187u, 317, 2, 1);
        break;
    case 27:
        load(ctx, 0x0181520eu, 318, 2, 1);
        load(ctx, 0x0181524fu, 319, 2, 1);
        load(ctx, 0x01815290u, 320, 2, 1);
        load(ctx, 0x018152d1u, 321, 2, 1);
        load(ctx, 0x01815312u, 322, 2, 1);
        break;
    case 28:
        load(ctx, 0x018153b5u, 323, 2, 1);
        load(ctx, 0x018153f6u, 324, 2, 1);
        load(ctx, 0x01815437u, 325, 2, 1);
        load(ctx, 0x01815478u, 326, 2, 1);
        load(ctx, 0x018154b9u, 327, 2, 1);
        break;
    case 29:
        load(ctx, 0x01813444u, 225, 2, 1);
        load(ctx, 0x01813485u, 226, 2, 1);
        load(ctx, 0x018134c6u, 227, 2, 1);
        load(ctx, 0x01813507u, 228, 2, 1);
        load(ctx, 0x01813548u, 229, 2, 1);
        break;
    case 30:
        load(ctx, 0x01812fbau, 210, 2, 1);
        load(ctx, 0x01812ffbu, 211, 2, 1);
        load(ctx, 0x0181303cu, 212, 2, 1);
        load(ctx, 0x0181307du, 213, 2, 1);
        load(ctx, 0x018130beu, 214, 2, 1);
        break;
    case 31:
        load(ctx, 0x01815540u, 333, 2, 1);
        load(ctx, 0x01815581u, 334, 2, 1);
        load(ctx, 0x018155c2u, 335, 2, 1);
        break;
    case 32:
        load(ctx, 0x01815695u, 336, 2, 1);
        load(ctx, 0x018156d6u, 337, 2, 1);
        load(ctx, 0x01815717u, 338, 2, 1);
        load(ctx, 0x01815758u, 339, 2, 1);
        break;
    case 33:
        load(ctx, 0x0181583bu, 340, 2, 1);
        load(ctx, 0x0181587cu, 341, 2, 1);
        break;
    case 34:
        load(ctx, 0x018158f6u, 342, 2, 1);
        load(ctx, 0x01815937u, 343, 2, 1);
        load(ctx, 0x01815978u, 344, 2, 1);
        break;
    case 35:
        load(ctx, 0x01815a2au, 345, 2, 1);
        load(ctx, 0x01815a6bu, 346, 2, 1);
        load(ctx, 0x01815aacu, 347, 2, 1);
        break;
    case 36:
        load(ctx, 0x01815b42u, 348, 2, 1);
        load(ctx, 0x01815b83u, 349, 2, 1);
        load(ctx, 0x01815bc4u, 350, 2, 1);
        break;
    case 37:
        load(ctx, 0x01815c7eu, 351, 2, 1);
        load(ctx, 0x01815cbfu, 352, 2, 1);
        break;
    case 39:
        load(ctx, 0x01813444u, 225, 2, 1);
        load(ctx, 0x01813485u, 226, 2, 1);
        load(ctx, 0x018134c6u, 227, 2, 1);
        load(ctx, 0x01813507u, 228, 2, 1);
        load(ctx, 0x01813548u, 229, 2, 1);
        break;
    case 40:
        load(ctx, 0x01815b42u, 348, 2, 1);
        load(ctx, 0x01815b83u, 349, 2, 1);
        load(ctx, 0x01815bc4u, 350, 2, 1);
        break;
    case 41:
        load(ctx, 0x01815d87u, 353, 2, 1);
        load(ctx, 0x01815dc8u, 354, 2, 1);
        break;
    case 42:
        load(ctx, 0x01815e5eu, 355, 2, 1);
        load(ctx, 0x01815e9fu, 356, 2, 1);
        load(ctx, 0x01815ee0u, 357, 2, 1);
        load(ctx, 0x01815f21u, 358, 2, 1);
        load(ctx, 0x01815f62u, 359, 2, 1);
        break;
    case 43:
        load(ctx, 0x01816038u, 360, 2, 1);
        load(ctx, 0x01816079u, 361, 2, 1);
        load(ctx, 0x018160bau, 362, 2, 1);
        load(ctx, 0x018160fbu, 363, 2, 1);
        break;
    case 44:
        load(ctx, 0x01816191u, 364, 2, 1);
        load(ctx, 0x018161d2u, 365, 2, 1);
        load(ctx, 0x01816213u, 366, 2, 1);
        break;
    case 45:
        load(ctx, 0x018162a9u, 367, 2, 1);
        load(ctx, 0x018162eau, 368, 2, 1);
        load(ctx, 0x0181632bu, 369, 2, 1);
        break;
    case 46:
        load(ctx, 0x018163c1u, 372, 2, 1);
        load(ctx, 0x01816402u, 214, 2, 1);
        break;
    case 47:
        load(ctx, 0x0181648fu, 296, 2, 1);
        load(ctx, 0x018164d0u, 214, 2, 1);
        load(ctx, 0x01816511u, 371, 2, 1);
        break;
    case 48:
        load(ctx, 0x0181659eu, 370, 2, 1);
        load(ctx, 0x018165dfu, 374, 2, 1);
        load(ctx, 0x01816620u, 373, 2, 1);
        break;
    case 49:
        load(ctx, 0x01816828u, 387, 2, 1);
        load(ctx, 0x01816869u, 388, 2, 1);
        load(ctx, 0x018168aau, 389, 2, 1);
        break;
    case 50:
        load(ctx, 0x01816942u, 385, 2, 1);
        load(ctx, 0x01816983u, 386, 2, 1);
        break;
    case 51:
        load(ctx, 0x01816a1bu, 381, 2, 1);
        load(ctx, 0x01816a5cu, 382, 2, 1);
        load(ctx, 0x01816a9du, 383, 2, 1);
        break;
    case 52:
        load(ctx, 0x0181670eu, 390, 2, 1);
        load(ctx, 0x0181674fu, 391, 2, 1);
        load(ctx, 0x01816790u, 392, 2, 1);
        break;
    case 53:
        load(ctx, 0x01816b32u, 378, 2, 1);
        load(ctx, 0x01816b73u, 379, 2, 1);
        load(ctx, 0x01816bb4u, 380, 2, 1);
        break;
    case 54:
        load(ctx, 0x01816c4cu, 375, 2, 1);
        load(ctx, 0x01816c8du, 376, 2, 1);
        load(ctx, 0x01816cceu, 377, 2, 1);
        break;
    case 55:
        load(ctx, 0x01816d48u, 393, 2, 1);
        load(ctx, 0x01816d89u, 394, 2, 1);
        load(ctx, 0x01816dcau, 395, 2, 1);
        break;
    case 57:
        load(ctx, 0x01817107u, 402, 2, 1);
        load(ctx, 0x01817148u, 403, 2, 1);
        load(ctx, 0x01817189u, 404, 2, 1);
        break;
    case 58:
        load(ctx, 0x01817052u, 398, 2, 1);
        load(ctx, 0x01817093u, 401, 2, 1);
        break;
    case 59:
        load(ctx, 0x01816f1bu, 214, 2, 1);
        load(ctx, 0x01816f5cu, 398, 2, 1);
        load(ctx, 0x01816f9du, 399, 2, 1);
        load(ctx, 0x01816fdeu, 400, 2, 1);
        break;
    case 62:
        load(ctx, 0x01816e5fu, 396, 2, 1);
        load(ctx, 0x01816ea0u, 397, 2, 1);
        break;
    case 63:
        load(ctx, 0x018171fdu, 405, 2, 1);
        load(ctx, 0x0181723eu, 406, 2, 1);
        load(ctx, 0x0181727fu, 407, 2, 1);
        break;
    case 64:
        load(ctx, 0x018172f9u, 442, 2, 1);
        load(ctx, 0x0181733au, 443, 2, 1);
        load(ctx, 0x0181737bu, 444, 2, 1);
        break;
    case 65:
        load(ctx, 0x018173f2u, 408, 2, 1);
        load(ctx, 0x01817433u, 409, 2, 1);
        load(ctx, 0x01817474u, 410, 2, 1);
        load(ctx, 0x018174b5u, 411, 2, 1);
        load(ctx, 0x018174f6u, 412, 2, 1);
        break;
    case 66:
        load(ctx, 0x01817570u, 413, 2, 1);
        load(ctx, 0x018175b1u, 414, 2, 1);
        load(ctx, 0x018175f2u, 415, 2, 1);
        load(ctx, 0x01817633u, 416, 2, 1);
        break;
    case 67:
        load(ctx, 0x018176adu, 417, 2, 1);
        load(ctx, 0x018176eeu, 418, 2, 1);
        load(ctx, 0x0181772fu, 419, 2, 1);
        load(ctx, 0x01817770u, 420, 2, 1);
        load(ctx, 0x018177b1u, 421, 2, 1);
        load(ctx, 0x018177f2u, 422, 2, 1);
        load(ctx, 0x01817833u, 423, 2, 1);
        load(ctx, 0x01817874u, 424, 2, 1);
        load(ctx, 0x018178b5u, 425, 2, 1);
        load(ctx, 0x018178f6u, 426, 2, 1);
        break;
    case 68:
        load(ctx, 0x0181797fu, 427, 2, 1);
        load(ctx, 0x018179c0u, 428, 2, 1);
        load(ctx, 0x01817a01u, 429, 2, 1);
        load(ctx, 0x01817a42u, 430, 2, 1);
        load(ctx, 0x01817a83u, 431, 2, 1);
        break;
    case 69:
        load(ctx, 0x01817afdu, 432, 2, 1);
        load(ctx, 0x01817b3eu, 433, 2, 1);
        load(ctx, 0x01817b7fu, 434, 2, 1);
        load(ctx, 0x01817bc0u, 435, 2, 1);
        load(ctx, 0x01817c01u, 436, 2, 1);
        load(ctx, 0x01817c42u, 437, 2, 1);
        load(ctx, 0x01817c83u, 438, 2, 1);
        load(ctx, 0x01817cc4u, 439, 2, 1);
        load(ctx, 0x01817d05u, 440, 2, 1);
        load(ctx, 0x01817d46u, 441, 2, 1);
        break;
    case 70:
        load(ctx, 0x01812ea0u, 371, 2, 1);
        break;
    case 71:
        load(ctx, 0x01812ea0u, 371, 2, 1);
        break;
    case 72:
        load(ctx, 0x01812f2du, 372, 2, 1);
        break;
    case 73:
        load(ctx, 0x01817dcfu, 442, 2, 1);
        break;
    case 76:
        load(ctx, 0x01817ec1u, 443, 2, 1);
        load(ctx, 0x01817f02u, 444, 2, 1);
        break;
    case 77:
        load(ctx, 0x01817f76u, 445, 2, 1);
        load(ctx, 0x01817fb7u, 446, 2, 1);
        break;
    case 128:
        load(ctx, 0x0181802eu, 764, 1, 1);
        load(ctx, 0x0181806du, 765, 1, 1);
        break;
    case 129:
        load(ctx, 0x018180b1u, 766, 1, 1);
        load(ctx, 0x018180f0u, 767, 1, 1);
        load(ctx, 0x0181812fu, 768, 1, 1);
        break;
    case 130:
        load(ctx, 0x01818173u, 769, 1, 1);
        load(ctx, 0x018181b2u, 770, 1, 1);
        load(ctx, 0x018181f1u, 771, 1, 1);
        break;
    case 131:
        load(ctx, 0x01818235u, 772, 1, 1);
        load(ctx, 0x01818274u, 773, 1, 1);
        break;
    case 132:
        load(ctx, 0x018182b8u, 774, 1, 1);
        load(ctx, 0x018182f7u, 775, 1, 1);
        load(ctx, 0x01818336u, 776, 1, 1);
        break;
    case 133:
        load(ctx, 0x0181837au, 777, 1, 1);
        load(ctx, 0x018183b9u, 778, 1, 1);
        load(ctx, 0x018183f8u, 779, 1, 1);
        load(ctx, 0x01818437u, 780, 1, 1);
        load(ctx, 0x01818476u, 781, 1, 1);
        break;
    case 134:
        load(ctx, 0x018184bau, 782, 1, 1);
        load(ctx, 0x018184f9u, 783, 1, 1);
        load(ctx, 0x01818538u, 784, 1, 1);
        break;
    case 135:
        load(ctx, 0x0181857cu, 785, 1, 1);
        load(ctx, 0x018185bbu, 786, 1, 1);
        load(ctx, 0x018185fau, 784, 1, 1);
        break;
    case 136:
        load(ctx, 0x0181863eu, 794, 1, 1);
        load(ctx, 0x0181867du, 795, 1, 1);
        break;
    case 137:
        load(ctx, 0x018186c1u, 794, 1, 1);
        load(ctx, 0x01818700u, 795, 1, 1);
        break;
    case 138:
        load(ctx, 0x01818744u, 796, 1, 1);
        load(ctx, 0x01818783u, 795, 1, 1);
        break;
    case 139:
        load(ctx, 0x018187c7u, 797, 1, 1);
        load(ctx, 0x01818806u, 800, 1, 1);
        break;
    case 140:
        load(ctx, 0x0181884au, 798, 1, 1);
        load(ctx, 0x01818889u, 800, 1, 1);
        break;
    case 141:
        load(ctx, 0x018188cdu, 799, 1, 1);
        load(ctx, 0x0181890cu, 800, 1, 1);
        break;
    case 142:
        load(ctx, 0x01818950u, 801, 1, 1);
        load(ctx, 0x0181898fu, 804, 1, 1);
        load(ctx, 0x018189ceu, 805, 1, 1);
        break;
    case 143:
        load(ctx, 0x01818a12u, 802, 1, 1);
        load(ctx, 0x01818a51u, 804, 1, 1);
        load(ctx, 0x01818a90u, 805, 1, 1);
        break;
    case 144:
        load(ctx, 0x01818ad4u, 803, 1, 1);
        load(ctx, 0x01818b13u, 804, 1, 1);
        load(ctx, 0x01818b52u, 805, 1, 1);
        break;
    case 145:
        load(ctx, 0x01818b96u, 771, 1, 1);
        load(ctx, 0x01818bd5u, 823, 1, 1);
        load(ctx, 0x01818c14u, 824, 1, 1);
        break;
    case 146:
        load(ctx, 0x01818c58u, 831, 1, 1);
        load(ctx, 0x01818c97u, 832, 1, 1);
        load(ctx, 0x01818cd6u, 833, 1, 1);
        break;
    case 147:
        load(ctx, 0x01818d1au, 825, 1, 1);
        load(ctx, 0x01818d59u, 826, 1, 1);
        break;
    case 148:
        load(ctx, 0x01818d9du, 244, 1, 1);
        load(ctx, 0x01818ddcu, 827, 1, 1);
        load(ctx, 0x01818e1bu, 828, 1, 1);
        break;
    case 149:
        load(ctx, 0x01818e5fu, 829, 1, 1);
        load(ctx, 0x01818e9eu, 830, 1, 1);
        load(ctx, 0x01818eddu, 364, 1, 1);
        break;
    case 150:
        load(ctx, 0x01818f21u, 834, 1, 1);
        load(ctx, 0x01818f60u, 835, 1, 1);
        load(ctx, 0x01818f9fu, 836, 1, 1);
        load(ctx, 0x01818fdeu, 837, 1, 1);
        load(ctx, 0x0181901du, 838, 1, 1);
        load(ctx, 0x0181905cu, 839, 1, 1);
        load(ctx, 0x0181909bu, 840, 1, 1);
        load(ctx, 0x018190dau, 841, 1, 1);
        break;
    case 155:
        load(ctx, 0x0181911eu, 851, 4, 1);
        load(ctx, 0x0181915du, 852, 4, 1);
        load(ctx, 0x0181919cu, 853, 4, 1);
        load(ctx, 0x018191dbu, 854, 4, 1);
        load(ctx, 0x0181921au, 855, 4, 1);
        load(ctx, 0x01819259u, 856, 4, 1);
        load(ctx, 0x01819298u, 857, 4, 1);
        load(ctx, 0x018192d7u, 858, 4, 1);
        break;
    case 156:
        load(ctx, 0x0181931du, 282, 2, 1);
        load(ctx, 0x0181935eu, 283, 2, 1);
        load(ctx, 0x0181939fu, 284, 2, 1);
        load(ctx, 0x018193e0u, 285, 2, 1);
        load(ctx, 0x01819421u, 286, 2, 1);
        break;
    case 157:
        load(ctx, 0x0181948au, 865, 4, 1);
        load(ctx, 0x018194c9u, 866, 4, 1);
        load(ctx, 0x01819508u, 867, 4, 1);
        load(ctx, 0x01819547u, 870, 4, 1);
        load(ctx, 0x01819586u, 868, 4, 1);
        load(ctx, 0x018195c5u, 869, 4, 1);
        break;
    case 158:
        load(ctx, 0x01819609u, 871, 4, 1);
        load(ctx, 0x01819648u, 872, 4, 1);
        load(ctx, 0x01819687u, 873, 4, 1);
        load(ctx, 0x018196c6u, 874, 4, 1);
        load(ctx, 0x01819705u, 875, 4, 1);
        load(ctx, 0x01819744u, 876, 4, 1);
        break;
    case 159:
        load(ctx, 0x01819788u, 877, 4, 1);
        load(ctx, 0x018197c7u, 878, 4, 1);
        load(ctx, 0x01819806u, 879, 4, 1);
        load(ctx, 0x01819845u, 880, 4, 1);
        load(ctx, 0x01819884u, 881, 4, 1);
        load(ctx, 0x018198c3u, 882, 4, 1);
        break;
    case 160:
        load(ctx, 0x01819907u, 883, 4, 1);
        load(ctx, 0x01819946u, 884, 4, 1);
        load(ctx, 0x01819985u, 885, 4, 1);
        load(ctx, 0x018199c4u, 886, 4, 1);
        load(ctx, 0x01819a03u, 887, 4, 1);
        load(ctx, 0x01819a42u, 888, 4, 1);
        break;
    case 162:
        load(ctx, 0x01819a86u, 889, 4, 1);
        load(ctx, 0x01819ac5u, 890, 4, 1);
        load(ctx, 0x01819b04u, 891, 4, 1);
        load(ctx, 0x01819b43u, 892, 4, 1);
        load(ctx, 0x01819b82u, 893, 4, 1);
        load(ctx, 0x01819bc1u, 894, 4, 1);
        load(ctx, 0x01819c00u, 895, 4, 1);
        break;
    case 189:
        load(ctx, 0x01819cc7u, 902, 4, 1);
        load(ctx, 0x01819d06u, 903, 4, 1);
        break;
    case 190:
        load(ctx, 0x01819c44u, 904, 4, 1);
        load(ctx, 0x01819c83u, 905, 4, 1);
        break;
    case 191:
        load(ctx, 0x01819d4au, 900, 4, 1);
        load(ctx, 0x01819d89u, 901, 4, 1);
        break;
    case 209:
        load(ctx, 0x01819dcdu, 958, 4, 1);
        load(ctx, 0x01819e0cu, 959, 4, 1);
        load(ctx, 0x01819e4bu, 960, 4, 1);
        break;
    case 210:
        load(ctx, 0x01819e8fu, 961, 4, 1);
        load(ctx, 0x01819eceu, 962, 4, 1);
        load(ctx, 0x01819f0du, 963, 4, 1);
        break;
    case 211:
        load(ctx, 0x01819f51u, 964, 4, 1);
        load(ctx, 0x01819f90u, 965, 4, 1);
        load(ctx, 0x01819fcfu, 966, 4, 1);
        load(ctx, 0x0181a00eu, 967, 4, 1);
        load(ctx, 0x0181a04du, 968, 4, 1);
        break;
    case 212:
        load(ctx, 0x0181a091u, 969, 4, 1);
        load(ctx, 0x0181a0d0u, 970, 4, 1);
        load(ctx, 0x0181a10fu, 971, 4, 1);
        load(ctx, 0x0181a14eu, 972, 4, 1);
        break;
    case 213:
        load(ctx, 0x0181a192u, 973, 4, 1);
        load(ctx, 0x0181a1d1u, 974, 4, 1);
        load(ctx, 0x0181a210u, 975, 4, 1);
        load(ctx, 0x0181a24fu, 976, 4, 1);
        break;
    case 214:
        load(ctx, 0x0181a293u, 977, 4, 1);
        load(ctx, 0x0181a2d2u, 978, 4, 1);
        load(ctx, 0x0181a311u, 979, 4, 1);
        load(ctx, 0x0181a350u, 980, 4, 1);
        break;
    case 215:
        load(ctx, 0x0181a394u, 981, 4, 1);
        load(ctx, 0x0181a3d3u, 982, 4, 1);
        load(ctx, 0x0181a412u, 983, 4, 1);
        load(ctx, 0x0181a451u, 984, 4, 1);
        break;
    case 216:
        load(ctx, 0x0181a495u, 981, 4, 1);
        load(ctx, 0x0181a4d4u, 982, 4, 1);
        load(ctx, 0x0181a513u, 984, 4, 1);
        load(ctx, 0x0181a552u, 985, 4, 1);
        break;
    case 217:
        load(ctx, 0x0181a596u, 993, 4, 1);
        load(ctx, 0x0181a5d5u, 994, 4, 1);
        load(ctx, 0x0181a614u, 995, 4, 1);
        break;
    case 218:
        load(ctx, 0x0181a658u, 996, 4, 1);
        load(ctx, 0x0181a697u, 997, 4, 1);
        load(ctx, 0x0181a6d6u, 998, 4, 1);
        load(ctx, 0x0181a715u, 999, 4, 1);
        load(ctx, 0x0181a754u, 1000, 4, 1);
        break;
    case 219:
        load(ctx, 0x0181a798u, 1001, 4, 1);
        load(ctx, 0x0181a7d7u, 1002, 4, 1);
        load(ctx, 0x0181a816u, 1003, 4, 1);
        load(ctx, 0x0181a855u, 1004, 4, 1);
        load(ctx, 0x0181a894u, 1005, 4, 1);
        break;
    case 220:
        load(ctx, 0x0181a8d8u, 1028, 4, 1);
        load(ctx, 0x0181a917u, 1029, 4, 1);
        load(ctx, 0x0181a956u, 1030, 4, 1);
        load(ctx, 0x0181a995u, 1031, 4, 1);
        load(ctx, 0x0181a9d4u, 1032, 4, 1);
        break;
    case 221:
        load(ctx, 0x0181aa18u, 1038, 4, 1);
        load(ctx, 0x0181aa57u, 1039, 4, 1);
        load(ctx, 0x0181aa96u, 1040, 4, 1);
        load(ctx, 0x0181aad5u, 1041, 4, 1);
        load(ctx, 0x0181ab14u, 1042, 4, 1);
        break;
    case 222:
        load(ctx, 0x0181ab58u, 1033, 4, 1);
        load(ctx, 0x0181ab97u, 1034, 4, 1);
        load(ctx, 0x0181abd6u, 1035, 4, 1);
        load(ctx, 0x0181ac15u, 1036, 4, 1);
        load(ctx, 0x0181ac54u, 1037, 4, 1);
        break;
    case 223:
        load(ctx, 0x0181ae17u, 1043, 4, 1);
        load(ctx, 0x0181ae56u, 1044, 4, 1);
        load(ctx, 0x0181ae95u, 1045, 4, 1);
        load(ctx, 0x0181aed4u, 1046, 4, 1);
        load(ctx, 0x0181af13u, 1047, 4, 1);
        load(ctx, 0x0181af52u, 1048, 4, 1);
        break;
    case 224:
        load(ctx, 0x0181ac98u, 1018, 4, 1);
        load(ctx, 0x0181acd7u, 1019, 4, 1);
        load(ctx, 0x0181ad16u, 1020, 4, 1);
        load(ctx, 0x0181ad55u, 1021, 4, 1);
        load(ctx, 0x0181ad94u, 1022, 4, 1);
        load(ctx, 0x0181add3u, 1023, 4, 1);
        break;
    case 225:
        load(ctx, 0x0181af96u, 1024, 4, 1);
        load(ctx, 0x0181afd5u, 1025, 4, 1);
        load(ctx, 0x0181b014u, 1026, 4, 1);
        load(ctx, 0x0181b053u, 1027, 4, 1);
        break;
    case 226:
        load(ctx, 0x0181b097u, 1006, 4, 1);
        load(ctx, 0x0181b0d6u, 1007, 4, 1);
        load(ctx, 0x0181b115u, 1008, 4, 1);
        load(ctx, 0x0181b154u, 1009, 4, 1);
        load(ctx, 0x0181b193u, 1010, 4, 1);
        load(ctx, 0x0181b1d2u, 1011, 4, 1);
        break;
    case 227:
        load(ctx, 0x0181b216u, 1012, 4, 1);
        load(ctx, 0x0181b255u, 1013, 4, 1);
        load(ctx, 0x0181b294u, 1014, 4, 1);
        load(ctx, 0x0181b2d3u, 1015, 4, 1);
        load(ctx, 0x0181b312u, 1016, 4, 1);
        load(ctx, 0x0181b351u, 1017, 4, 1);
        break;
    case 229:
        load(ctx, 0x0181b395u, 1049, 4, 1);
        load(ctx, 0x0181b3d4u, 1050, 4, 1);
        load(ctx, 0x0181b413u, 1051, 4, 1);
        break;
    case 230:
        load(ctx, 0x0181b395u, 1049, 4, 1);
        load(ctx, 0x0181b3d4u, 1050, 4, 1);
        load(ctx, 0x0181b413u, 1051, 4, 1);
        break;
    case 231:
        load(ctx, 0x0181b395u, 1049, 4, 1);
        load(ctx, 0x0181b3d4u, 1050, 4, 1);
        load(ctx, 0x0181b413u, 1051, 4, 1);
        break;
    case 232:
        load(ctx, 0x0181b395u, 1049, 4, 1);
        load(ctx, 0x0181b3d4u, 1050, 4, 1);
        load(ctx, 0x0181b413u, 1051, 4, 1);
        break;
    case 233:
        load(ctx, 0x0181b395u, 1049, 4, 1);
        load(ctx, 0x0181b3d4u, 1050, 4, 1);
        load(ctx, 0x0181b413u, 1051, 4, 1);
        break;
    case 239:
        load(ctx, 0x0181b457u, 1055, 4, 1);
        load(ctx, 0x0181b496u, 1056, 4, 1);
        load(ctx, 0x0181b4d5u, 1057, 4, 1);
        load(ctx, 0x0181b514u, 1058, 1, 1);
        break;
    case 240:
        load(ctx, 0x0181b558u, 1059, 4, 1);
        load(ctx, 0x0181b597u, 1060, 4, 1);
        load(ctx, 0x0181b5d6u, 1061, 4, 1);
        load(ctx, 0x0181b615u, 1062, 1, 1);
        break;
    case 241:
        load(ctx, 0x0181b659u, 1063, 4, 1);
        load(ctx, 0x0181b698u, 1064, 4, 1);
        load(ctx, 0x0181b6d7u, 1065, 4, 1);
        load(ctx, 0x0181b716u, 1066, 1, 1);
        break;
    case 242:
        load(ctx, 0x0181ac98u, 1018, 4, 1);
        load(ctx, 0x0181acd7u, 1019, 4, 1);
        load(ctx, 0x0181ad16u, 1020, 4, 1);
        load(ctx, 0x0181ad55u, 1021, 4, 1);
        load(ctx, 0x0181ad94u, 1022, 4, 1);
        load(ctx, 0x0181add3u, 1023, 4, 1);
        break;
    case 243:
        load(ctx, 0x0181ae17u, 1043, 4, 1);
        load(ctx, 0x0181ae56u, 1044, 4, 1);
        load(ctx, 0x0181ae95u, 1045, 4, 1);
        load(ctx, 0x0181aed4u, 1046, 4, 1);
        load(ctx, 0x0181af13u, 1047, 4, 1);
        load(ctx, 0x0181af52u, 1048, 4, 1);
        break;
    case 244:
        load(ctx, 0x0181af96u, 1024, 4, 1);
        load(ctx, 0x0181afd5u, 1025, 4, 1);
        load(ctx, 0x0181b014u, 1026, 4, 1);
        load(ctx, 0x0181b053u, 1027, 4, 1);
        break;
    case 245:
        load(ctx, 0x0181b097u, 1006, 4, 1);
        load(ctx, 0x0181b0d6u, 1007, 4, 1);
        load(ctx, 0x0181b115u, 1008, 4, 1);
        load(ctx, 0x0181b154u, 1009, 4, 1);
        load(ctx, 0x0181b193u, 1010, 4, 1);
        load(ctx, 0x0181b1d2u, 1011, 4, 1);
        break;
    case 246:
        load(ctx, 0x0181b216u, 1012, 4, 1);
        load(ctx, 0x0181b255u, 1013, 4, 1);
        load(ctx, 0x0181b294u, 1014, 4, 1);
        load(ctx, 0x0181b2d3u, 1015, 4, 1);
        load(ctx, 0x0181b312u, 1016, 4, 1);
        load(ctx, 0x0181b351u, 1017, 4, 1);
        break;
    case 256:
        load(ctx, 0x0181b75au, 524, 1, 1);
        load(ctx, 0x0181b799u, 525, 1, 1);
        load(ctx, 0x0181b7d8u, 526, 1, 1);
        load(ctx, 0x0181b817u, 527, 1, 1);
        load(ctx, 0x0181b856u, 528, 1, 1);
        break;
    case 257:
        load(ctx, 0x0181b89au, 605, 1, 1);
        load(ctx, 0x0181b8d9u, 606, 1, 1);
        load(ctx, 0x0181b918u, 608, 1, 1);
        load(ctx, 0x0181b957u, 609, 1, 1);
        load(ctx, 0x0181b996u, 610, 1, 1);
        break;
    case 258:
        load(ctx, 0x0181b9dau, 476, 1, 1);
        load(ctx, 0x0181ba19u, 479, 1, 1);
        load(ctx, 0x0181ba58u, 480, 1, 1);
        load(ctx, 0x0181ba97u, 475, 1, 1);
        load(ctx, 0x0181bad6u, 477, 1, 1);
        load(ctx, 0x0181bb15u, 478, 1, 1);
        break;
    case 259:
        load(ctx, 0x0181bb59u, 1075, 4, 1);
        load(ctx, 0x0181bb98u, 1076, 4, 1);
        load(ctx, 0x0181bbd7u, 1077, 4, 1);
        break;
    case 260:
        load(ctx, 0x0181bc1bu, 1078, 4, 1);
        load(ctx, 0x0181bc5au, 1079, 4, 1);
        load(ctx, 0x0181bc99u, 1080, 4, 1);
        break;
    case 261:
        load(ctx, 0x0181bcddu, 1081, 4, 1);
        load(ctx, 0x0181bd1cu, 1082, 4, 1);
        load(ctx, 0x0181bd5bu, 1083, 4, 1);
        break;
    case 262:
        load(ctx, 0x0181bd9fu, 1084, 4, 1);
        load(ctx, 0x0181bddeu, 1085, 4, 1);
        load(ctx, 0x0181be1du, 1086, 4, 1);
        load(ctx, 0x0181be5cu, 1087, 4, 1);
        load(ctx, 0x0181be9bu, 1088, 4, 1);
        load(ctx, 0x0181bedau, 1089, 4, 1);
        break;
    case 269:
        load(ctx, 0x0181bf1eu, 1102, 4, 1);
        load(ctx, 0x0181bf5du, 1103, 4, 1);
        break;
    case 270:
        load(ctx, 0x0181bf1eu, 1102, 4, 1);
        load(ctx, 0x0181bf5du, 1103, 4, 1);
        break;
    case 271:
        load(ctx, 0x0181bf1eu, 1102, 4, 1);
        load(ctx, 0x0181bf5du, 1103, 4, 1);
        break;
    case 272:
        load(ctx, 0x0181bf1eu, 1102, 4, 1);
        load(ctx, 0x0181bf5du, 1103, 4, 1);
        break;
    case 273:
        load(ctx, 0x0181bfa1u, 1121, 4, 1);
        load(ctx, 0x0181bfe0u, 1122, 4, 1);
        load(ctx, 0x0181c01fu, 1123, 4, 1);
        break;
    case 274:
        load(ctx, 0x0181c063u, 1124, 4, 1);
        load(ctx, 0x0181c0a2u, 1125, 4, 1);
        load(ctx, 0x0181c0e1u, 1126, 4, 1);
        break;
    case 275:
        load(ctx, 0x0181c125u, 1127, 4, 1);
        load(ctx, 0x0181c164u, 1128, 4, 1);
        load(ctx, 0x0181c1a3u, 1129, 4, 1);
        break;
    case 276:
        load(ctx, 0x0181c1e7u, 1130, 4, 1);
        load(ctx, 0x0181c226u, 1131, 4, 1);
        load(ctx, 0x0181c265u, 1132, 4, 1);
        load(ctx, 0x0181c2a4u, 1133, 4, 1);
        break;
    case 285:
        load(ctx, 0x0180b499u, 1158, 1, 1);
        load(ctx, 0x0180b4cfu, 1159, 1, 1);
        break;
    case 286:
        load(ctx, 0x0180b5aau, 1160, 1, 1);
        load(ctx, 0x0180b5e6u, 1161, 1, 1);
        break;
    case 287:
        load(ctx, 0x0180b6cau, 1162, 1, 1);
        load(ctx, 0x0180b709u, 1163, 1, 1);
        break;
    case 288:
        load(ctx, 0x0180b80du, 1155, 1, 1);
        load(ctx, 0x0180b84cu, 1156, 1, 1);
        load(ctx, 0x0180b88bu, 1157, 1, 1);
        break;
    case 289:
        load(ctx, 0x0180ba79u, 1143, 1, 1);
        load(ctx, 0x0180bab8u, 1144, 1, 1);
        load(ctx, 0x0180baf7u, 1145, 1, 1);
        load(ctx, 0x0180bb36u, 1146, 1, 1);
        load(ctx, 0x0180bb75u, 1147, 1, 1);
        load(ctx, 0x0180bbb4u, 1148, 1, 1);
        load(ctx, 0x0180bbf3u, 1149, 1, 1);
        load(ctx, 0x0180bc32u, 1150, 1, 1);
        load(ctx, 0x0180bc71u, 1151, 1, 1);
        load(ctx, 0x0180bcb0u, 1152, 1, 1);
        load(ctx, 0x0180bcefu, 1153, 1, 1);
        load(ctx, 0x0180bd2eu, 1154, 1, 1);
        break;
    case 290:
        load(ctx, 0x0180bd92u, 1137, 1, 1);
        load(ctx, 0x0180bdd1u, 1138, 1, 1);
        load(ctx, 0x0180be10u, 1139, 1, 1);
        load(ctx, 0x0180be4fu, 1140, 1, 1);
        break;
    case 291:
        load(ctx, 0x0180b499u, 1158, 1, 1);
        load(ctx, 0x0180b4cfu, 1159, 1, 1);
        break;
    case 292:
        load(ctx, 0x0180b5aau, 1160, 1, 1);
        load(ctx, 0x0180b5e6u, 1161, 1, 1);
        break;
    case 293:
        load(ctx, 0x0180b6cau, 1162, 1, 1);
        load(ctx, 0x0180b709u, 1163, 1, 1);
        break;
    case 298:
        load(ctx, 0x0181c2e8u, 1164, 4, 1);
        load(ctx, 0x0181c327u, 1165, 4, 1);
        load(ctx, 0x0181c366u, 1166, 4, 1);
        break;
    case 299:
        load(ctx, 0x0181c3aau, 1167, 4, 1);
        load(ctx, 0x0181c3e9u, 1168, 4, 1);
        load(ctx, 0x0181c428u, 1169, 4, 1);
        break;
    case 300:
        load(ctx, 0x0181c46cu, 1170, 4, 1);
        load(ctx, 0x0181c4abu, 1171, 4, 1);
        load(ctx, 0x0181c4eau, 1172, 4, 1);
        break;
    case 301:
        load(ctx, 0x0181c52eu, 1175, 4, 1);
        load(ctx, 0x0181c56du, 1176, 4, 1);
        load(ctx, 0x0181c5acu, 1177, 4, 1);
        load(ctx, 0x0181c5ebu, 1178, 4, 1);
        load(ctx, 0x0181c62au, 1179, 4, 1);
        load(ctx, 0x0181c669u, 1180, 4, 1);
        load(ctx, 0x0181c6a8u, 1181, 4, 1);
        load(ctx, 0x0181c6e7u, 1182, 4, 1);
        load(ctx, 0x0181c726u, 1183, 4, 1);
        load(ctx, 0x0181c765u, 1184, 4, 1);
        load(ctx, 0x0181c7a4u, 1185, 4, 1);
        load(ctx, 0x0181c7e3u, 1186, 4, 1);
        break;
    case 303:
        load(ctx, 0x0181c827u, 1187, 4, 1);
        load(ctx, 0x0181c866u, 1188, 4, 1);
        load(ctx, 0x0181c8a5u, 1189, 4, 1);
        load(ctx, 0x0181c8e4u, 1190, 4, 1);
        load(ctx, 0x0181c923u, 1191, 4, 1);
        break;
    case 304:
        load(ctx, 0x0181c967u, 1192, 4, 1);
        load(ctx, 0x0181c9a6u, 1193, 4, 1);
        load(ctx, 0x0181c9e5u, 1194, 4, 1);
        load(ctx, 0x0181ca24u, 1195, 4, 1);
        break;
    case 305:
        load(ctx, 0x0181ca68u, 1196, 4, 1);
        load(ctx, 0x0181caa7u, 1197, 4, 1);
        load(ctx, 0x0181cae6u, 1198, 4, 1);
        load(ctx, 0x0181cb25u, 1199, 4, 1);
        break;
    case 310:
        load(ctx, 0x0181cb69u, 1085, 4, 1);
        break;
    case 314:
        load(ctx, 0x01813936u, 240, 2, 1);
        load(ctx, 0x01813977u, 241, 2, 1);
        break;
    case 315:
        load(ctx, 0x01813c76u, 250, 2, 1);
        load(ctx, 0x01813cb7u, 251, 2, 1);
        load(ctx, 0x01813cf8u, 252, 2, 1);
        load(ctx, 0x01813d39u, 253, 2, 1);
        load(ctx, 0x01813d7au, 254, 2, 1);
        break;
    case 316:
        load(ctx, 0x01813aebu, 245, 2, 1);
        load(ctx, 0x01813b2cu, 246, 2, 1);
        load(ctx, 0x01813b6du, 247, 2, 1);
        load(ctx, 0x01813baeu, 248, 2, 1);
        load(ctx, 0x01813befu, 249, 2, 1);
        break;
    case 317:
        load(ctx, 0x01813145u, 215, 2, 1);
        load(ctx, 0x01813186u, 216, 2, 1);
        load(ctx, 0x018131c7u, 217, 2, 1);
        load(ctx, 0x01813208u, 218, 2, 1);
        load(ctx, 0x01813249u, 219, 2, 1);
        break;
    case 318:
        load(ctx, 0x018139e2u, 242, 2, 1);
        load(ctx, 0x01813a23u, 243, 2, 1);
        load(ctx, 0x01813a64u, 244, 2, 1);
        break;
    case 319:
        load(ctx, 0x01813620u, 230, 2, 1);
        load(ctx, 0x01813661u, 231, 2, 1);
        load(ctx, 0x018136a2u, 232, 2, 1);
        load(ctx, 0x018136e3u, 233, 2, 1);
        load(ctx, 0x01813724u, 234, 2, 1);
        break;
    case 320:
        load(ctx, 0x01812fbau, 210, 2, 1);
        load(ctx, 0x01812ffbu, 211, 2, 1);
        load(ctx, 0x0181303cu, 212, 2, 1);
        load(ctx, 0x0181307du, 213, 2, 1);
        load(ctx, 0x018130beu, 214, 2, 1);
        break;
    case 321:
        load(ctx, 0x01813444u, 225, 2, 1);
        load(ctx, 0x01813485u, 226, 2, 1);
        load(ctx, 0x018134c6u, 227, 2, 1);
        load(ctx, 0x01813507u, 228, 2, 1);
        load(ctx, 0x01813548u, 229, 2, 1);
        break;
    case 322:
        load(ctx, 0x01813e01u, 255, 2, 1);
        load(ctx, 0x01813e42u, 256, 2, 1);
        load(ctx, 0x01813e83u, 257, 2, 1);
        load(ctx, 0x01813ec4u, 258, 2, 1);
        load(ctx, 0x01813f05u, 259, 2, 1);
        break;
    case 323:
        load(ctx, 0x0181cbadu, 1217, 4, 1);
        load(ctx, 0x0181cbecu, 1218, 4, 1);
        load(ctx, 0x0181cc2bu, 1219, 4, 1);
        load(ctx, 0x0181cc6au, 1220, 4, 1);
        break;
    case 324:
        load(ctx, 0x0181ccaeu, 1221, 4, 1);
        load(ctx, 0x0181ccedu, 1222, 4, 1);
        load(ctx, 0x0181cd2cu, 1223, 4, 1);
        load(ctx, 0x0181cd6bu, 1224, 4, 1);
        break;
    case 325:
        load(ctx, 0x0181cdafu, 1225, 4, 1);
        load(ctx, 0x0181cdeeu, 1226, 4, 1);
        load(ctx, 0x0181ce2du, 1227, 4, 1);
        load(ctx, 0x0181ce6cu, 1228, 4, 1);
        break;
    case 326:
        load(ctx, 0x0181ceb0u, 1229, 4, 1);
        load(ctx, 0x0181ceefu, 1230, 4, 1);
        load(ctx, 0x0181cf2eu, 1231, 4, 1);
        load(ctx, 0x0181cf6du, 1232, 4, 1);
        break;
    case 327:
        load(ctx, 0x0181cfb1u, 1240, 4, 1);
        load(ctx, 0x0181cff0u, 1241, 4, 1);
        load(ctx, 0x0181d02fu, 1242, 4, 1);
        load(ctx, 0x0181d06eu, 1243, 4, 1);
        load(ctx, 0x0181d0adu, 1244, 4, 1);
        load(ctx, 0x0181d0ecu, 1245, 4, 1);
        load(ctx, 0x0181d12bu, 1246, 4, 1);
        break;
    case 328:
        load(ctx, 0x0181cfb1u, 1240, 4, 1);
        load(ctx, 0x0181cff0u, 1241, 4, 1);
        load(ctx, 0x0181d02fu, 1242, 4, 1);
        load(ctx, 0x0181d06eu, 1243, 4, 1);
        load(ctx, 0x0181d0adu, 1244, 4, 1);
        load(ctx, 0x0181d0ecu, 1245, 4, 1);
        load(ctx, 0x0181d12bu, 1246, 4, 1);
        break;
    case 329:
        load(ctx, 0x0181cfb1u, 1240, 4, 1);
        load(ctx, 0x0181cff0u, 1241, 4, 1);
        load(ctx, 0x0181d02fu, 1242, 4, 1);
        load(ctx, 0x0181d06eu, 1243, 4, 1);
        load(ctx, 0x0181d0adu, 1244, 4, 1);
        load(ctx, 0x0181d0ecu, 1245, 4, 1);
        load(ctx, 0x0181d12bu, 1246, 4, 1);
        break;
    case 330:
        load(ctx, 0x0181d16fu, 1247, 4, 1);
        load(ctx, 0x0181d1aeu, 1248, 4, 1);
        load(ctx, 0x0181d1edu, 1249, 4, 1);
        load(ctx, 0x0181d22cu, 1251, 4, 1);
        load(ctx, 0x0181d26bu, 1252, 4, 1);
        load(ctx, 0x0181d2aau, 1253, 4, 1);
        load(ctx, 0x0181d2e9u, 1254, 4, 1);
        load(ctx, 0x0181d328u, 1250, 4, 1);
        break;
    case 331:
        load(ctx, 0x0181d36cu, 1255, 4, 1);
        load(ctx, 0x0181d3abu, 1256, 4, 1);
        load(ctx, 0x0181d3eau, 1257, 4, 1);
        load(ctx, 0x0181d429u, 1258, 4, 1);
        load(ctx, 0x0181d468u, 1259, 4, 1);
        load(ctx, 0x0181d4a7u, 1260, 4, 1);
        load(ctx, 0x0181d4e6u, 1261, 4, 1);
        break;
    case 337:
        load(ctx, 0x0181d52au, 1269, 4, 1);
        load(ctx, 0x0181d569u, 1270, 4, 1);
        load(ctx, 0x0181d5a8u, 1271, 4, 1);
        break;
    case 338:
        load(ctx, 0x0181d5ecu, 1272, 4, 1);
        load(ctx, 0x0181d62bu, 1273, 4, 1);
        load(ctx, 0x0181d66au, 1274, 4, 1);
        break;
    case 339:
        load(ctx, 0x0181d6aeu, 1275, 4, 1);
        load(ctx, 0x0181d6edu, 1276, 4, 1);
        load(ctx, 0x0181d72cu, 1277, 4, 1);
        break;
    case 340:
        load(ctx, 0x0181d770u, 1278, 4, 1);
        load(ctx, 0x0181d7afu, 1279, 4, 1);
        load(ctx, 0x0181d7eeu, 1280, 4, 1);
        break;
    case 341:
        load(ctx, 0x0181d832u, 1281, 4, 1);
        load(ctx, 0x0181d871u, 1284, 4, 1);
        load(ctx, 0x0181d8b0u, 1282, 4, 1);
        load(ctx, 0x0181d8efu, 1283, 4, 1);
        break;
    case 342:
        load(ctx, 0x0181d933u, 1285, 4, 1);
        load(ctx, 0x0181d972u, 1288, 4, 1);
        load(ctx, 0x0181d9b1u, 1286, 4, 1);
        load(ctx, 0x0181d9f0u, 1287, 4, 1);
        break;
    case 348:
        load(ctx, 0x0181583bu, 340, 2, 1);
        load(ctx, 0x0181587cu, 341, 2, 1);
        break;
    case 349:
        load(ctx, 0x018158f6u, 342, 2, 1);
        load(ctx, 0x01815937u, 343, 2, 1);
        load(ctx, 0x01815978u, 344, 2, 1);
        break;
    case 350:
        load(ctx, 0x0181583bu, 340, 2, 1);
        load(ctx, 0x0181587cu, 341, 2, 1);
        break;
    case 351:
        load(ctx, 0x01815a2au, 345, 2, 1);
        load(ctx, 0x01815a6bu, 346, 2, 1);
        load(ctx, 0x01815aacu, 347, 2, 1);
        break;
    case 352:
        load(ctx, 0x0181583bu, 340, 2, 1);
        load(ctx, 0x0181587cu, 341, 2, 1);
        break;
    case 353:
        load(ctx, 0x01815b42u, 348, 2, 1);
        load(ctx, 0x01815b83u, 349, 2, 1);
        load(ctx, 0x01815bc4u, 350, 2, 1);
        break;
    case 354:
        load(ctx, 0x0181da34u, 1298, 4, 1);
        load(ctx, 0x0181da73u, 1299, 4, 1);
        load(ctx, 0x0181dab2u, 1300, 4, 1);
        break;
    case 355:
        load(ctx, 0x0181daf6u, 1301, 4, 1);
        load(ctx, 0x0181db35u, 1302, 4, 1);
        load(ctx, 0x0181db74u, 1303, 4, 1);
        break;
    case 356:
        load(ctx, 0x0181dbb8u, 1304, 4, 1);
        load(ctx, 0x0181dbf7u, 1305, 4, 1);
        load(ctx, 0x0181dc36u, 1306, 4, 1);
        break;
    case 364:
        load(ctx, 0x0181dc9au, 385, 2, 1);
        load(ctx, 0x0181dcdbu, 386, 2, 1);
        break;
    case 365:
        load(ctx, 0x0181dd93u, 390, 2, 1);
        load(ctx, 0x0181ddd4u, 391, 2, 1);
        load(ctx, 0x0181de15u, 392, 2, 1);
        break;
    case 366:
        load(ctx, 0x0181deadu, 381, 2, 1);
        load(ctx, 0x0181deeeu, 382, 2, 1);
        load(ctx, 0x0181df2fu, 383, 2, 1);
        break;
    case 367:
        load(ctx, 0x0181dfe4u, 390, 2, 1);
        load(ctx, 0x0181e025u, 391, 2, 1);
        load(ctx, 0x0181e066u, 392, 2, 1);
        break;
    case 368:
        load(ctx, 0x0181e0feu, 378, 2, 1);
        load(ctx, 0x0181e13fu, 379, 2, 1);
        load(ctx, 0x0181e180u, 380, 2, 1);
        break;
    case 369:
        load(ctx, 0x0181e218u, 375, 2, 1);
        load(ctx, 0x0181e259u, 376, 2, 1);
        load(ctx, 0x0181e29au, 377, 2, 1);
        break;
    case 370:
        load(ctx, 0x0181e314u, 395, 2, 1);
        break;
    case 372:
        load(ctx, 0x0181e3a8u, 1318, 2, 1);
        load(ctx, 0x0181e3e9u, 1320, 2, 1);
        load(ctx, 0x0181e42au, 1319, 2, 1);
        break;
    case 373:
        load(ctx, 0x0181e470u, 1321, 2, 1);
        load(ctx, 0x0181e4b1u, 1323, 2, 1);
        load(ctx, 0x0181e4f2u, 1322, 2, 1);
        break;
    case 374:
        load(ctx, 0x0181e538u, 1324, 2, 1);
        load(ctx, 0x0181e579u, 1326, 2, 1);
        load(ctx, 0x0181e5bau, 1325, 2, 1);
        break;
    case 417:
        load(ctx, 0x0181e600u, 1383, 2, 1);
        load(ctx, 0x0181e641u, 1384, 2, 1);
        load(ctx, 0x0181e682u, 1385, 2, 1);
        break;
    case 418:
        load(ctx, 0x0181e6c8u, 1386, 2, 1);
        load(ctx, 0x0181e709u, 1387, 2, 1);
        load(ctx, 0x0181e74au, 1388, 2, 1);
        break;
    case 419:
        load(ctx, 0x0181e790u, 1389, 2, 1);
        load(ctx, 0x0181e7d1u, 1390, 2, 1);
        load(ctx, 0x0181e812u, 1391, 2, 1);
        break;
    case 424:
        load(ctx, 0x0181e858u, 367, 2, 1);
        load(ctx, 0x0181e899u, 368, 2, 1);
        load(ctx, 0x0181e8dau, 369, 2, 1);
        break;
    case 425:
        load(ctx, 0x0181e954u, 360, 2, 1);
        load(ctx, 0x0181e995u, 361, 2, 1);
        load(ctx, 0x0181e9d6u, 362, 2, 1);
        load(ctx, 0x0181ea17u, 363, 2, 1);
        break;
    case 426:
        load(ctx, 0x0181ea91u, 364, 2, 1);
        load(ctx, 0x0181ead2u, 365, 2, 1);
        load(ctx, 0x0181eb13u, 366, 2, 1);
        break;
    case 427:
        load(ctx, 0x0181eb8du, 355, 2, 1);
        load(ctx, 0x0181ebceu, 356, 2, 1);
        load(ctx, 0x0181ec0fu, 357, 2, 1);
        load(ctx, 0x0181ec50u, 358, 2, 1);
        load(ctx, 0x0181ec91u, 359, 2, 1);
        break;
    case 431:
        load(ctx, 0x0181ed0bu, 1413, 2, 1);
        load(ctx, 0x0181ed4cu, 1414, 2, 1);
        load(ctx, 0x0181ed8du, 1415, 2, 1);
        break;
    case 432:
        load(ctx, 0x0181edd3u, 1416, 2, 1);
        load(ctx, 0x0181ee14u, 1417, 2, 1);
        load(ctx, 0x0181ee55u, 1418, 2, 1);
        break;
    case 433:
        load(ctx, 0x0181ee9bu, 1419, 2, 1);
        load(ctx, 0x0181eedcu, 1420, 2, 1);
        load(ctx, 0x0181ef1du, 1421, 2, 1);
        break;
    case 434:
        load(ctx, 0x0181ed0bu, 1413, 2, 1);
        load(ctx, 0x0181ed4cu, 1414, 2, 1);
        load(ctx, 0x0181ed8du, 1415, 2, 1);
        break;
    case 435:
        load(ctx, 0x0181edd3u, 1416, 2, 1);
        load(ctx, 0x0181ee14u, 1417, 2, 1);
        load(ctx, 0x0181ee55u, 1418, 2, 1);
        break;
    case 436:
        load(ctx, 0x0181ee9bu, 1419, 2, 1);
        load(ctx, 0x0181eedcu, 1420, 2, 1);
        load(ctx, 0x0181ef1du, 1421, 2, 1);
        break;
    case 446:
        load(ctx, 0x0181ef63u, 1432, 2, 1);
        load(ctx, 0x0181efa4u, 1433, 2, 1);
        load(ctx, 0x0181efe5u, 1434, 2, 1);
        load(ctx, 0x0181f026u, 1435, 2, 1);
        break;
    case 447:
        load(ctx, 0x0181f06cu, 1436, 2, 1);
        load(ctx, 0x0181f0adu, 1437, 2, 1);
        load(ctx, 0x0181f0eeu, 1438, 2, 1);
        load(ctx, 0x0181f12fu, 1439, 2, 1);
        break;
    case 448:
        load(ctx, 0x0181f175u, 1440, 2, 1);
        load(ctx, 0x0181f1b6u, 1441, 2, 1);
        load(ctx, 0x0181f1f7u, 1442, 2, 1);
        load(ctx, 0x0181f238u, 1443, 2, 1);
        break;
    default: break;
    }
}

void mu_audio_register_npc(int32_t type, int preloaded,
    void (*load)(void *, uint32_t, int32_t, int32_t, int32_t), void *ctx)
{
    if (preloaded || !load) return;
    switch (type) {
    case 2561:
        load(ctx, 0x01808e5au, 160, 1, 1);
        break;
    case 2566:
        load(ctx, 0x01808f26u, 160, 1, 1);
        break;
    case 2571:
        load(ctx, 0x01808ff8u, 161, 1, 1);
        break;
    case 2623:
        load(ctx, 0x0180a70eu, 512, 4, 1);
        break;
    case 2654:
        load(ctx, 0x01809cb2u, 859, 4, 1);
        load(ctx, 0x01809cf1u, 860, 4, 1);
        load(ctx, 0x01809d30u, 861, 4, 1);
        load(ctx, 0x01809d6fu, 862, 4, 1);
        load(ctx, 0x01809daeu, 863, 4, 1);
        break;
    case 2659:
        load(ctx, 0x01809e9bu, 864, 4, 1);
        break;
    case 2661:
        load(ctx, 0x01809f4eu, 906, 4, 1);
        break;
    case 2662:
        load(ctx, 0x01809fc7u, 907, 4, 1);
        break;
    case 2663:
        load(ctx, 0x0180a040u, 907, 4, 1);
        break;
    default: break;
    }
}
