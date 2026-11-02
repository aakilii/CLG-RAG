import os
import sys
import asyncio
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Set up paths
backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
sys.path.insert(0, backend_dir)

import db
import ai_service
import text_processor
import project_manager
from sklearn.cluster import KMeans
import numpy as np

PDF_FILENAME = "computer-science-and-programming-fundamentals.pdf"
PDF_PATH = os.path.join(backend_dir, "temp_uploads", PDF_FILENAME)

def create_cs_fundamentals_pdf():
    doc = SimpleDocTemplate(
        PDF_PATH,
        pagesize=letter,
        rightMargin=45,
        leftMargin=45,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1D1D1F"),
        spaceAfter=8
    )

    subtitle_style = ParagraphStyle(
        "DocSubTitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#6E6E73"),
        spaceAfter=14
    )

    h1_style = ParagraphStyle(
        "Heading1",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12.5,
        leading=16,
        textColor=colors.HexColor("#0071E3"),
        spaceBefore=8,
        spaceAfter=4
    )

    h2_style = ParagraphStyle(
        "Heading2",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#1D1D1F"),
        spaceBefore=6,
        spaceAfter=2
    )

    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#333336"),
        spaceAfter=5
    )

    story = []

    # PAGE 1: Python & C++ Core Fundamentals
    story.append(Paragraph("Computer Science & Programming Languages Fundamentals", title_style))
    story.append(Paragraph("Core Reference Guide: Python, C++, Java, JavaScript, Computer Architecture & Operating Systems", subtitle_style))

    story.append(Paragraph("1. Python Programming Language: Core Mechanics & Paradigms", h1_style))
    story.append(Paragraph("<b>Language Architecture & Dynamic Typing:</b> Python is a high-level, interpreted, dynamically typed language created by Guido van Rossum. In Python, variables are object references rather than fixed memory storage cells. Everything in Python is an object, including integers, functions, and modules. Type checking occurs at runtime. Python executes code by compiling source files into bytecode (.pyc), which is executed by the Python Virtual Machine (PVM).", body_style))
    story.append(Paragraph("<b>Memory Management & Global Interpreter Lock (GIL):</b> Python manages memory via a private heap space. Allocation is handled by Python's memory manager with an internal arena allocator (PyMalloc). Deallocation employs reference counting augmented by a cyclic generational garbage collector that identifies and frees cyclical references across 3 generations. CPython enforces the Global Interpreter Lock (GIL), a mutex preventing multiple native OS threads from executing Python bytecodes simultaneously, ensuring thread safety around CPython object state while requiring multiprocessing for CPU-bound parallelism.", body_style))
    story.append(Paragraph("<b>Data Structures:</b> Python features built-in mutable structures (Lists: dynamic arrays with amortized O(1) append; Dictionaries: hash tables using open addressing with O(1) average lookup; Sets: unique hashed elements) and immutable structures (Tuples, Strings, Bytes, Frozensets). List comprehensions and generator expressions provide declarative syntax. Generators use the <code>yield</code> keyword to produce lazy sequences with O(1) memory overhead.", body_style))
    story.append(Paragraph("<b>Object-Oriented & Functional Features:</b> Python supports classes, multiple inheritance with C3 Linearization Method Resolution Order (MRO), dunder methods (__init__, __str__, __repr__, __getitem__), properties (@property), and decorators (higher-order functions that take a callable and return a modified callable). First-class functions enable closures, lambda expressions, map(), and filter().", body_style))

    story.append(Paragraph("2. C++ Programming Language: Systems Programming & Low-Level Control", h1_style))
    story.append(Paragraph("<b>Language Philosophy & Compilation:</b> C++ is a statically typed, compiled, multi-paradigm language created by Bjarne Stroustrup as an extension of C. It follows the 'zero-overhead principle': what you don't use, you don't pay for. The compilation pipeline consists of the Preprocessor (#include, #define macros), Compiler (translates C++ source to assembly/machine code), Assembler (produces object files .o/.obj), and Linker (resolves symbols and libraries into executables).", body_style))
    story.append(Paragraph("<b>Pointers, References, & Memory Layout:</b> In C++, memory is divided into the Stack (automatic allocation, fast LIFO structure for local variables and call frames) and the Heap (dynamic manual allocation via <code>new</code> and <code>delete</code> or <code>malloc</code> and <code>free</code>). Pointers hold the direct memory address of a variable and can be null or reassigned; references (<code>T&amp;</code>) are immutable aliases to existing objects that cannot be null. Memory leaks occur when heap-allocated memory is not released.", body_style))
    story.append(Paragraph("<b>RAII & Modern Smart Pointers:</b> Resource Acquisition Is Initialization (RAII) ties resource lifespan (memory, file handles, sockets, mutexes) to object lifespan on the stack. Destructors automatically release resources when variables exit scope. Modern C++ (C++11 and beyond) deprecates raw pointer ownership in favor of Smart Pointers from <code>&lt;memory&gt;</code>: <code>std::unique_ptr</code> (exclusive ownership, move-only, zero runtime overhead), <code>std::shared_ptr</code> (reference-counted shared ownership), and <code>std::weak_ptr</code> (non-owning observer preventing circular references).", body_style))
    story.append(Paragraph("<b>Object-Oriented Programming & Templates:</b> C++ supports polymorphism via virtual functions and Virtual Method Tables (vtables). Virtual destructors are mandatory for base classes to prevent undefined behavior upon polymorphic deletion. Templates provide compile-time parametric polymorphism (generics) and metaprogramming. The Standard Template Library (STL) provides containers (vector, list, map, unordered_map) and generic algorithms.", body_style))

    story.append(PageBreak())

    # PAGE 2: Java & JavaScript Runtime Environments
    story.append(Paragraph("3. Java Programming Language: JVM Ecosystem & Enterprise OOP", h1_style))
    story.append(Paragraph("<b>Java Platform & 'Write Once, Run Anywhere':</b> Java is a class-based, object-oriented, statically typed language developed by James Gosling at Sun Microsystems. Java achieves platform independence via the Java Virtual Machine (JVM). Java source code (.java) compiles via <code>javac</code> into platform-neutral bytecode (.class). The JVM executes bytecode using an interpreter combined with a Just-In-Time (JIT) compiler (HotSpot C1/C2 compilers) that analyzes execution profiles and compiles frequently called 'hot' methods into optimized native machine code.", body_style))
    story.append(Paragraph("<b>JVM Architecture & Memory Areas:</b> The JVM memory layout comprises: (1) Heap: shared runtime data area where all class instances and arrays are allocated; (2) Method Area / Metaspace: stores per-class structures, field and method data, bytecode; (3) JVM Stacks: per-thread call frames holding local variables and partial results; (4) Program Counter (PC) Registers: tracks current instruction address; (5) Native Method Stacks. Java utilizes automatic Garbage Collection (e.g. G1GC, ZGC) using generational hypotheses (Young Gen: Eden, Survivor spaces; Old / Tenured Gen).", body_style))
    story.append(Paragraph("<b>Four Pillars of Java OOP:</b> (1) Encapsulation: bundling fields with methods and restricting direct access using access modifiers (private, package-private, protected, public); (2) Abstraction: hiding complex implementation details using interfaces and abstract classes; (3) Inheritance: deriving new classes from existing classes using <code>extends</code> (single class inheritance); (4) Polymorphism: method overloading (compile-time) and method overriding (runtime dynamic dispatch).", body_style))
    story.append(Paragraph("<b>Collections Framework & Concurrency:</b> The Java Collections Framework provides interfaces (List, Set, Map, Queue) and implementations (ArrayList: resizable array; LinkedList: doubly-linked list; HashMap: buckets using hashing with linked-list/red-black tree collision resolution; ConcurrentHashMap: thread-safe concurrent buckets). Concurrency primitives include threads, Runnable, Callable, ExecutorService, synchronization blocks, and ReentrantLocks.", body_style))

    story.append(Paragraph("4. JavaScript & TypeScript: Web Architecture & Asynchronous Event Loop", h1_style))
    story.append(Paragraph("<b>Language Foundation & Engines:</b> JavaScript (ECMAScript) is a lightweight, interpreted, just-in-time compiled, prototype-based language created by Brendan Eich. It is single-threaded and non-blocking by design. Modern JavaScript engines like Google's V8 (in Chrome and Node.js) compile JavaScript directly to machine code using Ignition (interpreter) and TurboFan (optimizing compiler), employing hidden classes and inline caching for fast property access.", body_style))
    story.append(Paragraph("<b>The Event Loop & Concurrency Model:</b> Because JavaScript has a single Call Stack, asynchronous operations (I/O, network requests, timers) are delegated to browser Web APIs or Node.js libuv threadpool. When operations complete, their callbacks are pushed onto Task Queues: (1) Microtask Queue (Promises, async/await, queueMicrotask, MutationObserver), which has top execution priority; (2) Macrotask Queue (setTimeout, setInterval, setImmediate, I/O events). The Event Loop constantly checks if the Call Stack is empty; if empty, it exhausts the entire Microtask Queue before executing the next Macrotask.", body_style))
    story.append(Paragraph("<b>Scope, Closures, & Prototypes:</b> Scope in JS can be global, function-level (var), or block-level (let, const). Hoisting moves variable and function declarations to the top of their scope. A Closure is the combination of a function bundled with references to its surrounding lexical environment, allowing inner functions to access outer variables even after the outer function has returned. Inheritance is prototypal: objects have internal [[Prototype]] links forming prototype chains terminating at Object.prototype.", body_style))
    story.append(Paragraph("<b>TypeScript & Modern ES Features:</b> TypeScript is a typed superset of JavaScript developed by Microsoft that compiles down to plain JS. It adds static type checking, interfaces, type aliases, union/intersection types, generics, and access modifiers. Modern ES6+ additions include arrow functions (lexical 'this'), destructuring, template literals, modules (import/export), Promises, and the async/await syntactic sugar.", body_style))

    story.append(PageBreak())

    # PAGE 3: Computer Architecture & Operating Systems
    story.append(Paragraph("5. Computer Hardware Architecture & Memory Hierarchy", h1_style))
    story.append(Paragraph("<b>Von Neumann Architecture & CPU Anatomy:</b> Modern digital computers are based on the Von Neumann model, consisting of: (1) Central Processing Unit (CPU) with an Arithmetic Logic Unit (ALU), Control Unit (CU), and internal Registers; (2) Main Memory (RAM); (3) Input/Output mechanisms; and (4) Secondary Storage. The CPU executes instructions via the instruction cycle: Fetch (load instruction from memory pointed to by Program Counter), Decode (determine opcode and operands), Execute (perform operation in ALU), and Writeback (store result to register or memory). Pipelining overlaps instruction phases to maximize throughput.", body_style))
    story.append(Paragraph("<b>Registers & Cache Hierarchy:</b> Storage performance follows an inverse pyramid of speed, cost, and capacity: (1) CPU Registers (~0.5 ns, a few dozen words); (2) Level 1 (L1) Cache (~1 ns, divided into L1 Instruction and L1 Data, ~32KB–64KB per core); (3) Level 2 (L2) Cache (~3–5 ns, ~512KB–1MB per core); (4) Level 3 (L3) Shared Cache (~10–20 ns, 16MB–64MB shared across cores); (5) Main Memory / RAM (~60–100 ns, DDR4/DDR5, 16GB–128GB); (6) Solid-State Drives / NVMe (~10–100 microseconds); (7) Magnetic Hard Drives (~5–10 milliseconds). Caches exploit Temporal Locality (recently accessed data is likely to be accessed again) and Spatial Locality (adjacent data is likely to be accessed soon). Cache line size is typically 64 bytes.", body_style))

    story.append(Paragraph("6. Operating Systems: Process Management, Memory & File Systems", h1_style))
    story.append(Paragraph("<b>Processes vs Threads:</b> A Process is an executing instance of a program with its own private virtual address space, memory segments (Text/Code, Initialized Data, BSS, Heap, Stack), file descriptors, and security context. A Thread is the smallest unit of execution scheduled by the OS kernel, residing within a process. All threads in a process share the same virtual address space, heap, and open file tables, but each thread has its own private Stack, Program Counter, and CPU Registers. Context switching between threads is faster than between processes because it avoids invalidating TLB (Translation Lookaside Buffer) page tables.", body_style))
    story.append(Paragraph("<b>CPU Scheduling & Concurrency:</b> OS Schedulers allocate CPU time slices using algorithms: First-Come-First-Served (FCFS), Shortest Job First (SJF), Round Robin (RR with time quantum), and Multi-Level Feedback Queues (MLFQ). Synchronization primitives prevent race conditions on shared data: Mutexes (mutual exclusion locks), Semaphores (counting locks), Spinlocks, and Condition Variables. Deadlocks occur when 4 Coffman conditions hold: Mutual Exclusion, Hold and Wait, No Preemption, and Circular Wait.", body_style))
    story.append(Paragraph("<b>Virtual Memory & Paging:</b> Operating systems isolate processes using Virtual Memory. The Memory Management Unit (MMU) translates virtual addresses to physical RAM frames using Page Tables and a hardware cache called the TLB. Typical page size is 4KB. When a process requests a page not currently in physical RAM, the MMU triggers a Page Fault interrupt; the kernel fetches the requested page from swap space on disk and updates the page table. Page replacement policies include LRU (Least Recently Used) and Clock algorithm.", body_style))

    story.append(PageBreak())

    # PAGE 4: Networking, Data Structures & Computational Complexity
    story.append(Paragraph("7. Computer Networking & Internet Protocols", h1_style))
    story.append(Paragraph("<b>OSI 7-Layer Model & TCP/IP Protocol Stack:</b> The OSI model outlines network communication across 7 layers: (7) Application (HTTP, DNS, SSH, SMTP); (6) Presentation (TLS/SSL encryption, JSON serialization); (5) Session (session management); (4) Transport (TCP, UDP); (3) Network (IP routing, ICMP); (2) Data Link (Ethernet, MAC addressing, Wi-Fi frames); (1) Physical (cables, radio frequencies, bits). In practice, the 4-layer TCP/IP stack collapses these into Application, Transport, Internet, and Network Access.", body_style))
    story.append(Paragraph("<b>TCP vs UDP & Connection Mechanics:</b> Transmission Control Protocol (TCP) is connection-oriented, reliable, and ordered. It uses a Three-Way Handshake to establish connections (SYN -&gt; SYN-ACK -&gt; ACK) and a Four-Way Handshake for termination (FIN -&gt; ACK -&gt; FIN -&gt; ACK). TCP provides flow control (sliding window protocol) and congestion control (Slow Start, Congestion Avoidance, Fast Retransmit). User Datagram Protocol (UDP) is connectionless, lightweight, and unordered, without delivery guarantees or retransmissions, making it ideal for real-time video streaming, DNS, and online gaming.", body_style))
    story.append(Paragraph("<b>DNS & HTTP Protocols:</b> Domain Name System (DNS) translates human-readable hostnames (e.g. google.com) into numerical IP addresses via recursive resolvers, root nameservers, TLD nameservers, and authoritative nameservers. HTTP/1.1 uses persistent TCP connections but suffers from head-of-line blocking. HTTP/2 introduces binary framing, multiplexing multiple requests over a single TCP connection, header compression (HPACK), and server push. HTTP/3 replaces TCP with QUIC over UDP to eliminate transport head-of-line blocking and achieve faster 0-RTT handshakes.", body_style))

    story.append(Paragraph("8. Data Structures, Algorithms & Computational Complexity", h1_style))
    story.append(Paragraph("<b>Asymptotic Complexity (Big-O Notation):</b> Big-O notation characterizes the upper bound of algorithm runtime or memory growth relative to input size (n). Common complexities: O(1) Constant (hash table lookup), O(log n) Logarithmic (binary search in sorted array), O(n) Linear (sequential scan), O(n log n) Linearithmic (MergeSort, QuickSort average), O(n^2) Quadratic (nested loops, BubbleSort), O(2^n) Exponential (naive recursive Fibonacci), O(n!) Factorial (travelling salesman brute force). Space complexity measures auxiliary memory required.", body_style))
    story.append(Paragraph("<b>Fundamental Data Structures:</b> (1) Arrays: contiguous memory, O(1) indexed access, O(n) insertion/deletion; (2) Linked Lists: nodes with pointers, O(1) insertion at head/tail, O(n) traversal; (3) Stacks &amp; Queues: LIFO and FIFO abstract data types; (4) Hash Tables: key-value mapping with hash function, O(1) average lookup; (5) Binary Search Trees (BST) &amp; Self-Balancing Trees (AVL, Red-Black): O(log n) search, insert, delete; (6) Heaps / Priority Queues: complete binary tree with min/max heap property, O(1) peek, O(log n) extract; (7) Graphs: vertices connected by edges (represented as adjacency matrix or adjacency list) traversed via Breadth-First Search (BFS, shortest path on unweighted graphs) and Depth-First Search (DFS, topological sorting, cycle detection).", body_style))

    doc.build(story)
    print(f"[PDF] Created {PDF_PATH} successfully.")

async def seed_database():
    os.makedirs(os.path.dirname(PDF_PATH), exist_ok=True)
    create_cs_fundamentals_pdf()

    # 1. Register note in database
    existing = db.supabase.table("notes").select("id, status").eq("filename", PDF_FILENAME).execute().data
    if existing:
        note_id = existing[0]["id"]
        print(f"[DB] Found existing note for {PDF_FILENAME}: {note_id}")
        chunks = db.get_chunks_for_note(note_id)
        if len(chunks) > 0:
            print(f"[DB] Note {note_id} already has {len(chunks)} chunks in Supabase!")
            # Ensure status is ready
            db.update_note_status(note_id, "ready")
            # Ensure projects have it
            projects = project_manager.list_projects()
            for p in projects:
                project_manager.add_doc_to_project(p["id"], note_id)
            print("[Projects] Associated CS Fundamentals document with all active projects.")
            return
    else:
        note = db.create_note(PDF_FILENAME)
        note_id = note["id"]
        print(f"[DB] Created note record: {note_id}")

    # 2. Extract text & chunk
    pages = text_processor.extract_text_from_pdf(PDF_PATH)
    chunks = text_processor.chunk_text(pages, chunk_size=450, overlap=80)
    print(f"[Extract] Extracted {len(pages)} pages into {len(chunks)} chunks.")

    # 3. Parallel Embeddings
    sem = asyncio.Semaphore(10)
    async def embed_with_limit(text):
        async with sem:
            return await ai_service.get_embedding(text)

    tasks = [embed_with_limit(item["content"]) for item in chunks]
    embeddings = await asyncio.gather(*tasks)

    chunks_to_insert = []
    for item, emb in zip(chunks, embeddings):
        chunks_to_insert.append({
            "note_id": note_id,
            "content": item["content"],
            "embedding": emb,
            "chunk_index": item["chunk_index"]
        })

    # 4. Insert chunks into Supabase
    db.insert_chunks(chunks_to_insert)
    db.update_note_status(note_id, "ready")
    print(f"[DB] Successfully inserted {len(chunks_to_insert)} chunks into Supabase pgvector.")

    # 5. Topic Clustering with KMeans and Groq
    if len(chunks_to_insert) >= 3:
        n_clusters = min(5, len(chunks_to_insert))
        mat = np.array(embeddings)
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto").fit(mat)
        labels = kmeans.labels_
        for c_idx in range(n_clusters):
            sample_texts = [chunks[i]["content"] for i, lbl in enumerate(labels) if lbl == c_idx]
            if sample_texts:
                topic_label = ai_service.label_topic_cluster(sample_texts)
                db.insert_topic(note_id, topic_label, c_idx)
                print(f"[Topics] Cluster {c_idx}: {topic_label}")

    # 6. Associate with projects
    projects = project_manager.list_projects()
    for p in projects:
        project_manager.add_doc_to_project(p["id"], note_id)
    print("[Projects] Associated CS Fundamentals document with all active projects.")

if __name__ == "__main__":
    asyncio.run(seed_database())
