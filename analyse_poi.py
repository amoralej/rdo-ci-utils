
import argparse
import re
import requests
import sys
import classify_console


def parse_args():
    parser = argparse.ArgumentParser(description='Process information about a puppet-openstack-integration job')
    parser.add_argument('-u', '--url', dest='url', help='URL of console log')
    return parser.parse_args()

INS_MOD_RE='Done \(install_modules.sh\)'
ins_mod_phase = { 're': 'Done \(install_modules.sh\)',
                  'phase': 'Puppet modules installation',
                }
first_puppet_phase = { 're': "Running Puppet Scenario: scenario00.? \(2nd time\)",
                       'phase': '1st puppet run',
                }
sec_puppet_phase = { 're': 'Prepare Tempest',
                       'phase': '2nd puppet run',
                }  
tempest_phase = { 're': 'Totals.*?Failed:[\ ]*([0-9]*)',
                       'phase': 'Tempest',
                }

phases = []
phases.append(tempest_phase)

def get_from_url(url):
    console = requests.get(url)
    if console.status_code == 200:
        return console.text
    else:
        print "ERROR: getting output from %s" % url
        sys.exit(1)


def get_console_from_file(path):
    file = open(path)
    console = file.read()
    return console


def analyze(console):
    re_repo ='.*delorean_url=(.*)/delorean.repo'
    repo = re.search(re_repo, console)
    print "Job using repo %s" % repo.group(1)
    re_success = 'Finished: SUCCESS' 
    job_success = re.search(re_success, console)
    if job_success:
        print "Job passed"
        return
    try:
        classified_error = classify_console.classify(console)[1]
        running_on = classify_console.classify(console)[0]
        print "Job running in: %s" % running_on
        print "Classified error: %s" % classified_error
    except:
        pass
    analyse_poi(console)

def details_first_puppet_run():
    re_job_name = "https://ci.centos.org/job/(.*)/consoleText"
    job_name = re.search(re_job_name, args.url).group(1)
    out_url = "https://ci.centos.org/artifacts/rdo/%s/weirdo-project/puppet.txt.gz" % job_name
    phase_out = get_from_url(out_url)
    re_phase = ".*\(err\).*"
    lines = re.finditer(re_phase, phase_out)
    for line in lines:
        print line.group()


def analyse_poi(console):
    for phase in ins_mod_phase, first_puppet_phase, sec_puppet_phase:
        regex = phase['re']
        phase_desc = phase['phase']
        phase_passed = re.search(regex, console)
        if phase_passed:
            print "Phase %s: OK" % phase_desc
        else:
            print "Phase %s: FAILED" % phase_desc
            if phase == first_puppet_phase:
                details_first_puppet_run()
            return 0

    for phase in [tempest_phase]:
        regex = phase['re']
        failed_regex = '{(0|1)}.*?FAILED\n'
        phase_desc = phase['phase']
        phase_passed = re.search(regex,console)
        if phase_passed:
            if phase_passed.group(1) == '0':
                print "Phase %s: OK" % phase_desc
            else:
                print "Phase %s: FAILED" % phase_desc
                print "List of failed tempest tests (%s):" % phase_passed.group(1)
                failures = re.finditer(failed_regex,console)
                for failure in failures:
                    print failure.group() 
        else:
            print "Phase %s: FAILED" % phase_desc
            print "Error running tempest: check logs after \"| Running Tempest\" line"


if __name__ == "__main__":
    args = parse_args()
    if args.url:
        console = get_from_url(args.url)
    analyze(console)
