/* Standalone entry point; mu-render links charsel_tool.c directly. */
int mu_charsel_tool_main(int argc, char **argv);
int main(int argc, char **argv)
{
    return mu_charsel_tool_main(argc, argv);
}
