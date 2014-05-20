from urllib.request import urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError
import json
import http.client
from threading import Thread
import copy
from base64 import b64encode

# ===============================================
#
# Test List
#
# ===============================================

VERBOSE = True
DEBUGGING = True

#JOBE_SERVER = 'localhost'
#JOBE_SERVER = '192.168.1.107'
JOBE_SERVER = "jobe.cosc.canterbury.ac.nz"

GOOD_TEST = 0
FAIL_TEST = 1
EXCEPTION = 2

TEST_SET = [

{
    'comment': 'Valid Python3',
    'language_id': 'python3',
    'sourcecode': r'''print("Hello world!")
''',
    'sourcefilename': 'test.py',
    'expect': { 'outcome': 15, 'stdout': 'Hello world!\n' }
},

{
    'comment': 'Python3 with stdin',
    'language_id': 'python3',
    'sourcecode': r'''print(input())
print(input())
''',
    'input': 'Line1\nLine2\n',
    'sourcefilename': 'test.py',
    'expect': { 'outcome': 15, 'stdout': 'Line1\nLine2\n' }
},

{
    'comment': 'Syntactically invalid Python3',
    'language_id': 'python3',
    'sourcecode': r'''print("Hello world!"
''',
    'sourcefilename': 'test.py',
    'expect': { 'outcome': 11 }
},

{
    'comment': 'Python3 runtime error',
    'language_id': 'python3',
    'sourcecode': r'''data = [1, 2]
print(data[2])
''',
    'sourcefilename': 'test.py',
    'expect': { 'outcome': 12 }
},

{
    'comment': 'Test good C hello world',
    'language_id': 'c',
    'sourcecode': r'''#include <stdio.h>
int main() {
    printf("Hello world\nIsn't this fun!\n");
}
''',
    'sourcefilename': 'prog.c',
    'expect': { 'outcome': 15, 'stdout': "Hello world\nIsn't this fun!\n" }
},

{
    'comment': 'Test compile error C hello world',
    'language_id': 'c',
    'sourcecode': r'''#include <stdio.h>
int main() {
    printf("Hello world\nIsn't this fun!\n")
}
''',
    'sourcefilename': 'prog.c',
    'expect': { 'outcome': 11 }
},

{
    'comment': 'Test runtime error C hello world',
    'language_id': 'c',
    'sourcecode': r'''#include <stdio.h>
int main() {
    printf("Hello world\nIsn't this fun!\n");
    char* s = NULL;
    printf("%c", *s);
}
''',
    'sourcefilename': 'prog.c',
    'expect': { 'outcome': 12 }
},

{
    'comment': 'Test timelimit on C',
    'language_id': 'c',
    'sourcecode': r'''#include <stdio.h>
int main() {
    while(1) {};
}
''',
    'sourcefilename': 'prog.c',
    'expect': { 'outcome': 13 }
},

{
    'comment': 'Memory limit exceeded in C (seg faults)',
    'language_id': 'c',
    'sourcecode': r'''#include <stdio.h>
#include <stdlib.h>
// Will try to allocate 100MB; default limit is 50MB
#define CHUNKSIZE 100000000

int main() {
    char* p = malloc(CHUNKSIZE);
    if (p == NULL) {
        printf("Memory limit worked\n");
    } else {
        printf("Oh dear, the malloc worked");
    }
}

''',
    'sourcefilename': 'prog.c',
    'expect': { 'outcome': 15, 'stdout': 'Memory limit worked\n' }
},

{
    'comment': 'Infinite recursion (stack error) on C',
    'language_id': 'c',
    'sourcecode': r'''#include <stdlib.h>
#include <assert.h>

void silly(int i) {
    int j = i + 1;
    if (j != 0) {
        silly(j);
    } else {
        silly(j + 1);
    }
}

int main() {
    silly(3);
}
''',
    'sourcefilename': 'prog.c',
    'expect': { 'outcome': 12 }
},

{
    'comment': 'Python3 program with support files',
    'language_id': 'python3',
    'files': [
        ('randomid0129798', 'The first file\nLine 2'),
        ('randomid0980128', 'Second file')],
    'sourcecode': r'''print(open('file1').read())
print(open('file2').read())
''',
    'file_list': [('randomid0129798', 'file1'),('randomid0980128', 'file2')],
    'sourcefilename': 'test.py',
    'expect': { 'outcome': 15, 'stdout': '''The first file
Line 2
Second file
'''}
},

#{
    #'comment': 'Python3 program with customised timeout',
    #'language_id': 'python3',
    #'sourcecode': r'''from time import clock
#t = clock()
#while clock() < t + 10: pass  # Wait 10 seconds
#print("Hello Python")
#''',
    #'sourcefilename': 'test.py',
    #'parameters': {'cputime':12},
    #'expect': { 'outcome': 15, 'stdout': '''Hello Python
#'''}
#},

{
    'comment': 'C program fork bomb',
    'language_id': 'c',
    'sourcecode': r'''#include <linux/unistd.h>
#include <unistd.h>
#include <stdio.h>
int sqr(int n) {
    if (n == 0) {
        return 0;
    }
    else {
        int i = 0;
        for (i = 0; i < 2000; i++)
            fork();
        return n * n;
    }
}

int main() {
    printf("sqr(0) = %d\n", sqr(0));
    printf("sqr(7) = %d\n", sqr(7));
}''',
    'sourcefilename': 'test.c',
    'parameters': {'numprocs': 1},
    'expect': { 'outcome': 15, 'stdout': '''sqr(0) = 0
sqr(7) = 49
''', 'stderr': ''}
}
#,
## This test currently breaks the runguard sandbox, so disabled.
#{
    #'comment': 'C program controlled forking',
    #'language_id': 'c',
    #'sourcecode': r'''#include <linux/unistd.h>
##include <unistd.h>
##include <stdio.h>
#int main() {
    #int successes = 0, failures = 0;
    #for (int i = 0; i < 1000; i++) {
        #int pid = fork();
        #if (pid == -1) {
            #failures += 1;
        #}
        #else if (pid == 0) {
            #while (1) {};  // Child loops
        #}
        #else {
            #successes += 1;
        #}
    #}
    #printf("%d forks succeeded, %d failed\n", successes, failures);
#}''',
    #'sourcefilename': 'test.c',
    #'parameters': { 'numprocs': 10 },
    #'expect': { 'outcome': 15, 'stdout': '9 forks succeeded, 991 failed\n' }
#}
]


def check_parallel_submissions():
    '''Check that we can submit several jobs at once to Jobe with
       the process limit set to 1 and still have no conflicts.
       Requires that cgroups be enabled and runguard be compiled to
       use that feature.
    '''
    NUM_SUBMITS = 3

    job = {
        'comment': 'C program to check parallel submissions',
        'language_id': 'c',
        'sourcecode': r'''#include <stdio.h>
#include <unistd.h>
int main() {
    printf("Hello 1\n");
    sleep(2);
    printf("Hello 2\n");
}''',
        'sourcefilename': 'test.c',
        'parameters': { 'numprocs': 1 },
        'expect': { 'outcome': 15, 'stdout': 'Hello 1\nHello 2\n' }
    }

    threads = []
    for child_num in range(NUM_SUBMITS):
        print("Doing child", child_num)
        def run_job():
            this_job = copy.deepcopy(job)
            this_job['comment'] += '. Child' + str(child_num)
            run_test(job)

        t = Thread(target=run_job)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()
    print("All done")




def is_correct_result(expected, got):
    '''True iff every key in the expected outcome exists in the
       actual outcome and the associated values are equal, too'''
    for key in expected:
        if key not in got or expected[key] != got[key]:
            return False
    return True

# =============================================================

def check_file(file_id):
    '''Checks if the given fileid exists on the server.
       Returns status: 200 denotes file exists, 404 denotes file not found.
    '''

    resource = '/jobe/index.php/restapi/files/' + file_id
    headers = {"Accept": "text/plain"}
    connect = http.client.HTTPConnection(JOBE_SERVER)
    connect.request('HEAD', resource, '', headers)
    try:
        response = connect.getresponse()
    except HTTPError: pass

    if VERBOSE:
        print("Response to getting status of file ", file_id, ':')
        content = ''
        if response.status != 204:
            content =  response.read(4096)
        print(response.status, response.reason, content)

    connect.close()
    return response.status


def put_file(file_desc):
    '''Put the given (file_id, contents) to the server. Throws
       an exception to be caught by caller if anything fails.
    '''
    file_id, contents = file_desc
    contentsb64 = b64encode(contents.encode('utf8')).decode(encoding='UTF-8')
    data = json.dumps({ 'file_contents' : contentsb64 })
    resource = '/jobe/index.php/restapi/files/' + file_id
    headers = {"Content-type": "application/json",
               "Accept": "text/plain"}
    connect = http.client.HTTPConnection(JOBE_SERVER)
    connect.request('PUT', resource, data, headers)
    response = connect.getresponse()
    if VERBOSE:
        print("Response to putting", file_id, ':')
        content = ''
        if response.status != 204:
            content =  response.read(4096)
        print(response.status, response.reason, content)

    connect.close()


def run_test(test):
    '''Execute the given test, checking the output'''
    runspec = {}
    for key in test:
        if key not in ['comment', 'expect', 'files']:
            runspec[key] = test[key]
    if DEBUGGING:
        runspec['debug'] = True

    # First put any files to the server
    for file_desc in test.get('files', []):
        put_file(file_desc)
        if check_file(file_desc[0]) != 204:
            print("******** Put file/check file failed. File not found.****")

    # Prepare the request

    resource = '/jobe/index.php/restapi/runs/'
    data = json.dumps({ 'run_spec' : runspec })
    headers = {"Content-type": "application/json",
               "Accept": "application/json"}
    response = None
    content = ''
    result = {}
    # Send the request
    try:
        connect = http.client.HTTPConnection(JOBE_SERVER)
        connect.request('POST', resource, data, headers)
        response = connect.getresponse()
        if response.status != 204:
            content = response.read().decode('utf8')
            if content:
                result = json.loads(content)
        connect.close()
        #print(response.status, response.reason, content)

    except (HTTPError, ValueError) as e:
        print("\n***************** HTTP ERROR ******************\n")
        print(test['comment'], end='')
        if response:
            print(' Response:', response.status, response.reason, content)
        else:
            print(e)
        return EXCEPTION

   # Lastly, check the response is as specified

    if is_correct_result(test['expect'], result):
        if VERBOSE:
            display_result(test['comment'], result)
        else:
            print(test['comment'] + ' OK')
        return GOOD_TEST
    else:
        print("\n***************** FAILED TEST ******************\n")
        print(result)
        display_result(test['comment'], result)
        print("\n************************************************\n")
        return FAIL_TEST


def display_result(comment, ro):
    '''Display the given result object'''
    print(comment)
    if not isinstance(ro, dict) or 'outcome' not in ro:
        print("Bad result object", ro)
        return

    outcomes = {
        0:  'Successful run',
        11: 'Compile error',
        12: 'Runtime error',
        13: 'Time limit exceeded',
        15: 'Successful run',
        17: 'Memory limit exceeded',
        19: 'Illegal system call',
        20: 'Internal error, please report'}

    code = ro['outcome']
    print("{}".format(outcomes[code]))
    print()
    if ro['cmpinfo']:
        print("Compiler output:")
        print(ro['cmpinfo'])
        print()
    else:
        if ro['stdout']:
            print("Output:")
            print(ro['stdout'])
        else:
            print("No output")
        if ro['stderr']:
            print()
            print("Error output:")
            print(ro['stderr'])



def main():
    '''Every home should have one'''
    counters = [0, 0, 0]  # Passes, fails, exceptions
    for test in TEST_SET:
        result = run_test(test)
        counters[result] += 1
        if VERBOSE:
            print('=====================================')

    print()
    print("{} tests, {} passed, {} failed, {} exceptions".format(
        len(TEST_SET), counters[0], counters[1], counters[2]))
    print("Checking parallel submissions")
    check_parallel_submissions()




main()

