/*
 * DAP fixture (C): dereferences a NULL pointer deterministically.
 *
 * Compile with debug info and no optimisation, then run:
 *
 *     cc -g -O0 -o bin/crash bin/crash.c && ./bin/crash
 *
 * Expected today: SIGSEGV in main() at the line marked BUG (u is NULL because
 * find_user() does not know id 99). Fix: handle the NULL result and exit 0.
 * The source is committed; the binary is not (see .gitignore).
 */
#include <stdio.h>
#include <stdlib.h>

struct user {
    int id;
    const char *name;
    const char *email;
};

static struct user USERS[] = {
    {1, "Ada Lovelace", "ada@example.com"},
    {2, "Grace Hopper", "grace@example.com"},
    {3, "Linus Torvalds", "linus@example.com"},
};

static const int WANTED_IDS[] = {1, 2, 99, 3};

static struct user *find_user(int id)
{
    size_t n = sizeof(USERS) / sizeof(USERS[0]);
    for (size_t i = 0; i < n; i++) {
        if (USERS[i].id == id) {
            return &USERS[i];
        }
    }
    return NULL;
}

int main(void)
{
    size_t n = sizeof(WANTED_IDS) / sizeof(WANTED_IDS[0]);
    for (size_t i = 0; i < n; i++) {
        struct user *u = find_user(WANTED_IDS[i]);
        printf("%3d: %s <%s>\n", WANTED_IDS[i], u->name, u->email); /* BUG: u may be NULL */
    }
    return 0;
}
