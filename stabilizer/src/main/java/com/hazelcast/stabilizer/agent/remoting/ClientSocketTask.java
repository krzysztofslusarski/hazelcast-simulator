package com.hazelcast.stabilizer.agent.remoting;


import com.hazelcast.stabilizer.Utils;
import com.hazelcast.stabilizer.agent.Agent;
import com.hazelcast.stabilizer.agent.workerjvm.WorkerJvm;
import com.hazelcast.stabilizer.agent.workerjvm.WorkerJvmManager;
import com.hazelcast.stabilizer.agent.workerjvm.WorkerJvmSettings;
import com.hazelcast.stabilizer.common.messaging.Message;
import com.hazelcast.stabilizer.tests.Failure;
import com.hazelcast.stabilizer.tests.TestSuite;
import com.hazelcast.stabilizer.worker.commands.Command;
import org.apache.log4j.Logger;

import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.net.Socket;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;

class ClientSocketTask implements Runnable {
    private final static Logger log = Logger.getLogger(ClientSocketTask.class);

    private final Socket clientSocket;
    private final Agent agent;
    private final AgentMessageProcessor agentMessageProcessor;

    ClientSocketTask(Socket clientSocket, Agent agent, AgentMessageProcessor agentMessageProcessor) {
        this.clientSocket = clientSocket;
        this.agent = agent;
        this.agentMessageProcessor = agentMessageProcessor;
    }

    @Override
    public void run() {
        try {
            ObjectOutputStream out = new ObjectOutputStream(clientSocket.getOutputStream());
            out.flush();

            ObjectInputStream in = new ObjectInputStream(clientSocket.getInputStream());
            AgentRemoteService.Service service = (AgentRemoteService.Service) in.readObject();

            Object result;
            try {
                result = execute(service, in);
            } catch (Exception e) {
                log.fatal(e);
                result = e;
            }

            out.writeObject(result);
            out.flush();
        } catch (Throwable e) {
            log.fatal(e);
        } finally {
            Utils.closeQuietly(clientSocket);
        }
    }

    private Object execute(AgentRemoteService.Service service, ObjectInputStream in) throws Exception {
        Object result = null;
        switch (service) {
            case SERVICE_SPAWN_WORKERS:
                WorkerJvmSettings settings = (WorkerJvmSettings) in.readObject();
                spawnWorkers(settings);
                break;
            case SERVICE_INIT_TESTSUITE:
                TestSuite testSuite = (TestSuite) in.readObject();
                initTestSuite(testSuite);
                break;
            case SERVICE_TERMINATE_WORKERS:
                terminateWorkers();
                break;
            case SERVICE_EXECUTE_ALL_WORKERS:
                Command testCommand = (Command) in.readObject();
                WorkerJvmManager workerJvmManager = agent.getWorkerJvmManager();
                result = workerJvmManager.executeOnAllWorkers(testCommand);
                break;
            case SERVICE_EXECUTE_SINGLE_WORKER:
                testCommand = (Command) in.readObject();
                workerJvmManager = agent.getWorkerJvmManager();
                result = workerJvmManager.executeOnSingleWorker(testCommand);
                break;
            case SERVICE_ECHO:
                String msg = (String) in.readObject();
                echo(msg);
                break;
            case SERVICE_GET_FAILURES:
                result = getFailures();
                break;
            case SERVICE_GET_ALL_WORKERS:
                result = new ArrayList<String>();
                Collection<WorkerJvm> workerJvms = agent.getWorkerJvmManager().getWorkerJvms();
                for (WorkerJvm workerJvm : workerJvms) {
                    ((List<String>)result).add(workerJvm.id);
                }
                break;
            case SERVICE_PROCESS_MESSAGE:
                Message message = (Message) in.readObject();
                agentMessageProcessor.submit(message);
                break;
            default:
                throw new RuntimeException("Unknown service:" + service);
        }
        return result;
    }

    private ArrayList<Failure> getFailures() {
        ArrayList<Failure> failures = new ArrayList<Failure>();
        agent.getWorkerJvmFailureMonitor().drainFailures(failures);
        return failures;
    }

    private void spawnWorkers(WorkerJvmSettings settings) throws Exception {
        try {
            agent.getWorkerJvmManager().spawn(settings);
        } catch (Exception e) {
            log.fatal("Failed to spawn workers from settings:" + settings, e);
            throw e;
        }
    }

    private void initTestSuite(TestSuite testSuite) throws Exception {
        try {
            agent.initTestSuite(testSuite);
        } catch (Exception e) {
            log.fatal("Failed to init testsuite: " + testSuite, e);
            throw e;
        }
    }

    private void terminateWorkers() throws Exception {
        try {
            agent.getWorkerJvmManager().terminateWorkers();
        } catch (Exception e) {
            log.fatal("Failed to terminateWorker workers", e);
            throw e;
        }
    }

    private void echo(String msg) throws Exception {
        try {
            agent.echo(msg);
        } catch (Exception e) {
            log.fatal("Failed to echo", e);
            throw e;
        }
    }
}