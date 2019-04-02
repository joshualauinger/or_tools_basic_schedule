import logging, sys, collections
from xml.dom.minidom import parse, parseString
from ortools.sat.python import visualization
from ortools.sat.python import cp_model

# Debug mode ?
logging.basicConfig(stream=sys.stderr, level=logging.INFO)


class Job():
    def __init__(self, job_id, release_date,
                 processing_time, due_date,
                 power_req, weight, mach_id):
        self.job_id = int(job_id)
        self.release_date = int(release_date)
        self.processing_time = int(processing_time)
        self.due_date = int(due_date)
        self.power_req = int(power_req)
        self.weight = float(weight)
        self.mach_id = int(mach_id)
        self.dep_on = []

    def add_job_dep(self, temp_dep_on):
        self.dep_on.append(int(temp_dep_on))


# Parse input file
try:
    dom = parse(open(sys.argv[1]))
    schedule_input = dom.documentElement
except IndexError:
    print("Please drag an XML file onto run.BAT...")


def main(schedule_input):
    schedule_input_nodes = cull_text_nodes(schedule_input.childNodes)
    machines = schedule_input_nodes[0]
    machine_nodes = cull_text_nodes(machines.childNodes)
    dependancy_nodes = cull_text_nodes(schedule_input_nodes[1].childNodes)
    max_power = machines.attributes['max_power'].value
    logging.debug("maximum Power: %s" % max_power)
    job_list = populate_job_list(machine_nodes, dependancy_nodes)

    model = cp_model.CpModel()
    horizon = sum([job.processing_time for job in job_list])
    # task type?
    task_type = collections.namedtuple('task_type', 'start end interval')
    all_tasks = populate_all_tasks(job_list, model, horizon, task_type)
    intervals = populate_intervals(job_list, all_tasks)
    model.AddNoOverlap(intervals)

    # Add precedence constraints (into own function?) byRef equiv?
    for job in job_list:
        for dep in job.dep_on:
            model.Add(all_tasks[job.mach_id, job.job_id].start >=
                      all_tasks[job.mach_id, dep].end)

    # Makespan objective.
    obj_var = model.NewIntVar(0, horizon, 'makespan')
    model.AddMaxEquality(
        obj_var,
        [all_tasks[(job.mach_id, len(job_list) - 1)].end for job in job_list])
    model.Minimize(obj_var)

    # Solve model.
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    print('Optimal Schedule Length: %i' % solver.ObjectiveValue())


def populate_intervals(job_list, all_tasks):
    intervals = []
    for job in job_list:
        intervals.append(all_tasks[job.mach_id, job.job_id].interval)
    logging.debug(intervals)
    return intervals


def populate_all_tasks(job_list, model, horizon, task_type):
    all_tasks = {}
    for job in job_list:
            start_var = model.NewIntVar(0, horizon, 'start_%i_%i'
                                        % (job.mach_id,
                                           job.job_id))
            duration = job.processing_time
            end_var = model.NewIntVar(0, horizon, 'end_%i_%i'
                                      % (job.mach_id,
                                         job.job_id))
            interval_var = model.NewIntervalVar(start_var, duration, end_var,
                                                'interval_%i_%i'
                                                % (job.mach_id, job.job_id))
            all_tasks[job.mach_id, job.job_id] = task_type(
                                                    start=start_var,
                                                    end=end_var,
                                                    interval=interval_var)
    logging.debug(all_tasks)
    return all_tasks


def populate_job_list(machine_nodes, dependancy_nodes):
    job_list = []
    for machine in machine_nodes:
        jobs = machine.childNodes[1]
        job_nodes = cull_text_nodes(jobs.childNodes)
        for job in job_nodes:
            temp_job = Job(job.attributes['job_id'].value[1:],  # remove 'J'
                           job.attributes['release_date'].value,
                           job.attributes['processing_time'].value,
                           job.attributes['due_date'].value,
                           job.attributes['power'].value,
                           job.attributes['weight'].value,
                           machine.attributes['mach_id'].value)
            for dep in dependancy_nodes:
                if temp_job.job_id == int(dep.attributes['job'].value[1:]):
                    temp_job.add_job_dep(dep.attributes['dep_on'].value[1:])
            job_list.append(temp_job)
    return job_list


# Pass the children of a node to remove blank text nodes
def cull_text_nodes(nodes):
    temp = []
    for node in nodes:
        if node.nodeType != node.TEXT_NODE:
            logging.debug(node.tagName)
            temp.append(node)
    number_of_nodes_culled = len(nodes) - len(temp)
    logging.debug("%d text nodes culled.." % number_of_nodes_culled)
    return temp


if __name__ == "__main__":
    main(schedule_input)
