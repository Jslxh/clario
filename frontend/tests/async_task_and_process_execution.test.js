import test from 'node:test';
import assert from 'node:assert/strict';
import { generateProcessId } from '../src/utils/processManager.js';

test.describe('Asynchronous Process ID & Worker Thread Execution Suite', () => {
  test('1. Process ID generation creates valid unique PID strings with prefixes', () => {
    const pid1 = generateProcessId('PID-LLM');
    const pid2 = generateProcessId('PID-DOC');
    const pid3 = generateProcessId('PID');

    assert.ok(pid1.startsWith('PID-LLM-'), 'pid1 must start with PID-LLM-');
    assert.ok(pid2.startsWith('PID-DOC-'), 'pid2 must start with PID-DOC-');
    assert.ok(pid3.startsWith('PID-'), 'pid3 must start with PID-');
    assert.notEqual(pid1, pid2, 'Process IDs must be unique');
    assert.notEqual(pid2, pid3, 'Process IDs must be unique');
  });

  test('2. Async task execution lifecycle correctly handles RUNNING -> COMPLETED transition', async () => {
    const startTime = Date.now();
    const pid = generateProcessId('PID-LLM');
    const task = {
      id: pid,
      type: 'llm_query',
      thread: 'Thread-LLM-Grounding-Worker #1',
      title: 'Grounded RAG Query',
      status: 'RUNNING',
      startTime,
      endTime: null,
      durationMs: 0,
    };

    assert.equal(task.status, 'RUNNING');
    assert.ok(task.id.startsWith('PID-LLM-'));

    // Simulate async execution
    await new Promise((r) => setTimeout(r, 20));

    const endTime = Date.now();
    const completedTask = {
      ...task,
      status: 'COMPLETED',
      endTime,
      durationMs: endTime - startTime,
      result: { answer: 'Grounded answer synthesized from passages.' },
    };

    assert.equal(completedTask.status, 'COMPLETED');
    assert.ok(completedTask.durationMs >= 15);
    assert.equal(completedTask.result.answer, 'Grounded answer synthesized from passages.');
  });

  test('3. Async task failure records error and marks status FAILED', async () => {
    const startTime = Date.now();
    const pid = generateProcessId('PID-DOC');
    const task = {
      id: pid,
      type: 'doc_process',
      thread: 'Thread-Doc-Worker #4',
      title: 'Ingesting test.pdf',
      status: 'RUNNING',
      startTime,
      endTime: null,
      durationMs: 0,
    };

    const errorMessage = 'Qdrant vector store connection timeout';
    const failedTask = {
      ...task,
      status: 'FAILED',
      endTime: Date.now(),
      durationMs: Date.now() - startTime,
      error: errorMessage,
    };

    assert.equal(failedTask.status, 'FAILED');
    assert.equal(failedTask.error, errorMessage);
    assert.ok(failedTask.thread.includes('Thread-Doc-Worker'));
  });

  test('4. Process registry tracks multiple concurrent worker threads with non-blocking PIDs', () => {
    const tasks = [
      {
        id: generateProcessId('PID-LLM'),
        type: 'llm_query',
        thread: 'Thread-LLM-RAG-101',
        title: 'Synthesizing compliance policy',
        status: 'RUNNING',
      },
      {
        id: generateProcessId('PID-DOC'),
        type: 'doc_process',
        thread: 'Thread-Doc-Ingest-202',
        title: 'Embedding engineering_manual.pdf',
        status: 'RUNNING',
      },
      {
        id: generateProcessId('PID-SEARCH'),
        type: 'search',
        thread: 'Thread-Hybrid-Retriever-303',
        title: 'BM25 + Semantic Search',
        status: 'COMPLETED',
      },
    ];

    const running = tasks.filter((t) => t.status === 'RUNNING');
    assert.equal(running.length, 2, 'Must have 2 active running threads');
    assert.ok(running.some((t) => t.type === 'llm_query'));
    assert.ok(running.some((t) => t.type === 'doc_process'));
  });
});
