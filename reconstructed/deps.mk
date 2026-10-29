# BUILD-DEPS-001: header dependencies for the reconstructed/* builds, included at the end of each
# Makefile. Each rule compiles all its sources in one call, which keeps -MMD output for the last source
# only, so after the call it runs $(DEPS): one -MM pass over the rule's .c prerequisites that writes
# <target>.d with every header they include. A header change then rebuilds exactly those targets.
DEPS = $(CC) $(CFLAGS) -MM -MP -MT $@ $(filter %.c,$^) > $@.d
-include $(wildcard *.d)
