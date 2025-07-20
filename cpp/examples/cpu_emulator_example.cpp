// cpu_emulator_example.cpp - Example of integrating retrobus_perfetto with a CPU emulator

#include <retrobus/retrobus_perfetto.hpp>
#include <iostream>
#include <vector>
#include <random>

// Simulated CPU state
struct Z80State {
    uint16_t pc = 0x0100;   // Program counter
    uint16_t sp = 0x7FFE;   // Stack pointer
    uint8_t a = 0;          // Accumulator
    uint8_t b = 0, c = 0;   // BC register pair
    uint8_t d = 0, e = 0;   // DE register pair
    uint8_t h = 0, l = 0;   // HL register pair
    
    struct {
        bool zero = false;
        bool carry = false;
        bool sign = false;
        bool parity = false;
    } flags;
    
    uint64_t cycle_count = 0;
};

// Simple memory system
class Memory {
    std::vector<uint8_t> ram;
    
public:
    Memory() : ram(65536, 0) {
        // Load some example "program"
        ram[0x0100] = 0x3E; // LD A, 42
        ram[0x0101] = 42;
        ram[0x0102] = 0xCD; // CALL 0x0200
        ram[0x0103] = 0x00;
        ram[0x0104] = 0x02;
        ram[0x0105] = 0x76; // HALT
        
        ram[0x0200] = 0x06; // LD B, 10
        ram[0x0201] = 10;
        ram[0x0202] = 0x05; // DEC B
        ram[0x0203] = 0xC9; // RET
    }
    
    uint8_t read(uint16_t addr) { return ram[addr]; }
    void write(uint16_t addr, uint8_t value) { ram[addr] = value; }
};

// CPU emulator with tracing
class Z80Emulator {
    Z80State cpu;
    Memory memory;
    retrobus::PerfettoTraceBuilder& trace_builder;
    uint64_t cpu_thread;
    uint64_t io_thread;
    uint64_t memory_counter;
    uint64_t cycle_counter;
    
    // Convert cycles to nanoseconds (4MHz CPU = 250ns per cycle)
    uint64_t cycles_to_ns(uint64_t cycles) {
        return cycles * 250;
    }
    
public:
    Z80Emulator(retrobus::PerfettoTraceBuilder& builder) 
        : trace_builder(builder) {
        cpu_thread = builder.add_thread("Z80 CPU");
        io_thread = builder.add_thread("I/O");
        memory_counter = builder.add_counter_track("Memory Accesses", "count");
        cycle_counter = builder.add_counter_track("CPU Cycles", "cycles");
    }
    
    void run() {
        std::cout << "Starting Z80 emulation...\n";
        
        int instruction_count = 0;
        int memory_accesses = 0;
        
        while (instruction_count < 10) { // Run 10 instructions max
            uint64_t start_cycles = cpu.cycle_count;
            uint16_t pc = cpu.pc;
            uint8_t opcode = memory.read(pc);
            
            // Start instruction trace
            auto timestamp = cycles_to_ns(cpu.cycle_count);
            std::string mnemonic = decode_instruction(opcode);
            
            auto event = trace_builder.begin_slice(cpu_thread, mnemonic, timestamp);
            
            // Add pre-execution state
            event.annotation("state")
                .pointer("PC", pc)
                .integer("opcode", opcode)
                .integer("A", cpu.a)
                .integer("B", cpu.b)
                .integer("C", cpu.c)
                .pointer("SP", cpu.sp);
            
            event.annotation("flags")
                .boolean("Z", cpu.flags.zero)
                .boolean("C", cpu.flags.carry)
                .boolean("S", cpu.flags.sign)
                .boolean("P", cpu.flags.parity);
            
            // Execute instruction
            execute_instruction(opcode, memory_accesses);
            
            // End instruction trace
            timestamp = cycles_to_ns(cpu.cycle_count);
            trace_builder.end_slice(cpu_thread, timestamp);
            
            // Update counters
            trace_builder.update_counter(cycle_counter, cpu.cycle_count, timestamp);
            trace_builder.update_counter(memory_counter, memory_accesses, timestamp);
            
            instruction_count++;
            
            // Stop on HALT
            if (opcode == 0x76) {
                std::cout << "CPU halted at PC=" << std::hex << pc << std::dec << "\n";
                break;
            }
        }
        
        std::cout << "Emulation complete. Executed " << instruction_count 
                  << " instructions in " << cpu.cycle_count << " cycles.\n";
    }
    
private:
    std::string decode_instruction(uint8_t opcode) {
        switch (opcode) {
            case 0x3E: return "LD A,n";
            case 0xCD: return "CALL nn";
            case 0x76: return "HALT";
            case 0x06: return "LD B,n";
            case 0x05: return "DEC B";
            case 0xC9: return "RET";
            default: return "UNKNOWN";
        }
    }
    
    void execute_instruction(uint8_t opcode, int& memory_accesses) {
        switch (opcode) {
            case 0x3E: { // LD A,n
                cpu.pc++;
                cpu.a = memory.read(cpu.pc);
                memory_accesses++;
                cpu.pc++;
                cpu.cycle_count += 7;
                break;
            }
            
            case 0xCD: { // CALL nn
                cpu.pc++;
                uint16_t addr = memory.read(cpu.pc);
                memory_accesses++;
                cpu.pc++;
                addr |= (memory.read(cpu.pc) << 8);
                memory_accesses++;
                cpu.pc++;
                
                // Push return address
                cpu.sp -= 2;
                memory.write(cpu.sp, cpu.pc & 0xFF);
                memory.write(cpu.sp + 1, cpu.pc >> 8);
                memory_accesses += 2;
                
                // Jump to subroutine
                cpu.pc = addr;
                cpu.cycle_count += 17;
                
                // Trace the call as a flow event
                uint64_t flow_id = addr;
                auto flow = trace_builder.add_flow(cpu_thread, "CALL", 
                                                   cycles_to_ns(cpu.cycle_count), flow_id);
                flow.add_annotation("target", addr)
                    .add_annotation("return_addr", cpu.pc);
                break;
            }
            
            case 0xC9: { // RET
                // Pop return address
                uint16_t addr = memory.read(cpu.sp);
                addr |= (memory.read(cpu.sp + 1) << 8);
                memory_accesses += 2;
                cpu.sp += 2;
                cpu.pc = addr;
                cpu.cycle_count += 10;
                
                // Complete the flow
                uint64_t flow_id = cpu.pc;
                trace_builder.add_flow(cpu_thread, "RET", 
                                       cycles_to_ns(cpu.cycle_count), flow_id, true);
                break;
            }
            
            case 0x06: { // LD B,n
                cpu.pc++;
                cpu.b = memory.read(cpu.pc);
                memory_accesses++;
                cpu.pc++;
                cpu.cycle_count += 7;
                break;
            }
            
            case 0x05: { // DEC B
                cpu.b--;
                cpu.flags.zero = (cpu.b == 0);
                cpu.flags.sign = (cpu.b & 0x80) != 0;
                cpu.pc++;
                cpu.cycle_count += 4;
                break;
            }
            
            case 0x76: { // HALT
                cpu.pc++;
                cpu.cycle_count += 4;
                break;
            }
            
            default: {
                std::cerr << "Unknown opcode: " << std::hex << (int)opcode << std::dec << "\n";
                cpu.pc++;
                cpu.cycle_count += 4;
                break;
            }
        }
    }
};

int main() {
    try {
        // Create trace builder
        retrobus::PerfettoTraceBuilder builder("Z80 Emulator Example");
        
        // Create and run emulator
        Z80Emulator emulator(builder);
        emulator.run();
        
        // Save trace
        std::cout << "\nSaving trace to z80_emulation.perfetto-trace\n";
        builder.save("z80_emulation.perfetto-trace");
        
        std::cout << "Trace saved successfully!\n";
        std::cout << "View it at https://ui.perfetto.dev\n";
        
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << "\n";
        return 1;
    }
    
    return 0;
}