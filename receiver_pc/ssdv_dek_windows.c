/* Dekoder SSDV dla Windows: pakiety 256 B na stdin -> JPEG na stdout. Jak ssdv_dek.c z Della + tryb binarny. Kod SSDV: Philip Heron, GPL v3. */
#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <io.h>
#include "ssdv.h"
int main(void) {
  _setmode(_fileno(stdin), _O_BINARY); _setmode(_fileno(stdout), _O_BINARY);
  ssdv_t s; static uint8_t pkt[SSDV_PKT_SIZE]; size_t n = 0;
  uint8_t *buf = malloc(1024 * 1024);
  ssdv_dec_init(&s); ssdv_dec_set_buffer(&s, buf, 1024 * 1024);
  while (fread(pkt, 1, SSDV_PKT_SIZE, stdin) == SSDV_PKT_SIZE) {
    int err; if (ssdv_dec_is_packet(pkt, &err) != 0) { fprintf(stderr, "zly pakiet\n"); continue; }
    ssdv_dec_feed(&s, pkt); n++;
  }
  uint8_t *jpg; size_t len;
  if (ssdv_dec_get_jpeg(&s, &jpg, &len) != SSDV_OK) { fprintf(stderr, "brak obrazu\n"); return 1; }
  fwrite(jpg, 1, len, stdout); fprintf(stderr, "pakietow %u, JPEG %u B\n", (unsigned)n, (unsigned)len); return 0;
}
