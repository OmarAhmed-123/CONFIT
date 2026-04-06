/**
 * Model Optimization Script
 * =========================
 * Compresses glTF files with Draco compression.
 * 
 * Usage:
 *   node scripts/optimize-models.js
 * 
 * Requirements:
 *   npm install -g gltf-pipeline
 */

const { execSync, spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

// Configuration
const CONFIG = {
  modelsDir: path.join(__dirname, '../public/models'),
  outputDir: path.join(__dirname, '../public/models/optimized'),
  compressionLevel: 10, // Max compression (0-10)
  generateLOD: true,
  lodLevels: [
    { name: 'lod0', decimation: 1.0 },    // Full quality
    { name: 'lod1', decimation: 0.5 },    // 50% polygons
    { name: 'lod2', decimation: 0.2 },    // 20% polygons
  ],
};

// Colors for console output
const colors = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  red: '\x1b[31m',
};

function log(message, color = 'reset') {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

// ===========================================
// Main Optimization Function
// ===========================================

async function optimizeModels() {
  log('\n========================================', 'blue');
  log('  3D Model Optimization Pipeline', 'blue');
  log('========================================\n', 'blue');

  // Ensure output directory exists
  if (!fs.existsSync(CONFIG.outputDir)) {
    fs.mkdirSync(CONFIG.outputDir, { recursive: true });
    log(`Created output directory: ${CONFIG.outputDir}`, 'green');
  }

  // Find all glTF files
  const files = findModelFiles(CONFIG.modelsDir);
  
  if (files.length === 0) {
    log('No glTF files found to optimize.', 'yellow');
    return;
  }

  log(`Found ${files.length} model(s) to process.\n`, 'blue');

  let totalSaved = 0;
  const results = [];

  for (const file of files) {
    const result = await optimizeModel(file);
    results.push(result);
    totalSaved += result.saved;
  }

  // Print summary
  printSummary(results, totalSaved);
}

// ===========================================
// Model Processing Functions
// ===========================================

function findModelFiles(dir) {
  const files = [];
  
  if (!fs.existsSync(dir)) {
    return files;
  }

  const items = fs.readdirSync(dir);
  
  for (const item of items) {
    const fullPath = path.join(dir, item);
    const stat = fs.statSync(fullPath);
    
    if (stat.isDirectory()) {
      // Skip optimized directory
      if (item !== 'optimized' && item !== 'previews') {
        files.push(...findModelFiles(fullPath));
      }
    } else if (item.endsWith('.glb') || item.endsWith('.gltf')) {
      files.push(fullPath);
    }
  }
  
  return files;
}

async function optimizeModel(inputPath) {
  const filename = path.basename(inputPath);
  const relativePath = path.relative(CONFIG.modelsDir, inputPath);
  const outputPath = path.join(CONFIG.outputDir, relativePath);
  
  // Ensure output subdirectory exists
  const outputDir = path.dirname(outputPath);
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  const inputSize = fs.statSync(inputPath).size;
  
  log(`Processing: ${filename}`, 'blue');
  log(`  Input: ${formatBytes(inputSize)}`, 'reset');

  try {
    // Step 1: Draco compression
    const compressedPath = await compressWithDraco(inputPath, outputPath);
    const compressedSize = fs.statSync(compressedPath).size;
    
    // Step 2: Generate LOD variants (optional)
    if (CONFIG.generateLOD) {
      await generateLODVariants(compressedPath, outputDir, filename);
    }

    const saved = inputSize - compressedSize;
    const percent = ((saved / inputSize) * 100).toFixed(1);

    log(`  Output: ${formatBytes(compressedSize)}`, 'reset');
    log(`  Saved: ${percent}% (${formatBytes(saved)})\n`, 'green');

    return {
      filename,
      inputSize,
      outputSize: compressedSize,
      saved,
      percent: parseFloat(percent),
      success: true,
    };
  } catch (error) {
    log(`  Error: ${error.message}\n`, 'red');
    
    return {
      filename,
      inputSize,
      outputSize: inputSize,
      saved: 0,
      percent: 0,
      success: false,
      error: error.message,
    };
  }
}

async function compressWithDraco(inputPath, outputPath) {
  // Check if gltf-pipeline is available
  try {
    execSync('gltf-pipeline --version', { stdio: 'ignore' });
  } catch {
    throw new Error('gltf-pipeline not found. Install with: npm install -g gltf-pipeline');
  }

  const command = [
    'gltf-pipeline',
    '-i', `"${inputPath}"`,
    '-o', `"${outputPath}"`,
    '--draco.compressMeshes',
    `--draco.compressionLevel ${CONFIG.compressionLevel}`,
  ].join(' ');

  try {
    execSync(command, { 
      stdio: 'pipe',
      shell: true,
      timeout: 60000, // 1 minute timeout
    });
    return outputPath;
  } catch (error) {
    // If Draco fails, try without compression
    log('  Draco compression failed, copying original...', 'yellow');
    fs.copyFileSync(inputPath, outputPath);
    return outputPath;
  }
}

async function generateLODVariants(sourcePath, outputDir, filename) {
  const baseName = path.parse(filename).name;
  const ext = path.parse(filename).ext;

  for (const lod of CONFIG.lodLevels) {
    if (lod.decimation === 1.0) continue; // Skip LOD0 (already created)

    const lodFilename = `${baseName}-${lod.name}${ext}`;
    const lodPath = path.join(outputDir, lodFilename);

    // For now, just copy the compressed file
    // In production, use mesh decimation tools like:
    // - Blender Python script
    // - Simplygon
    // - Meshlab
    fs.copyFileSync(sourcePath, lodPath);
    
    log(`  Generated: ${lodFilename}`, 'reset');
  }
}

// ===========================================
// Utility Functions
// ===========================================

function formatBytes(bytes) {
  if (bytes === 0) return '0 B';
  
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function printSummary(results, totalSaved) {
  log('\n========================================', 'blue');
  log('  Optimization Summary', 'blue');
  log('========================================', 'blue');

  const successful = results.filter(r => r.success);
  const failed = results.filter(r => !r.success);

  log(`\nProcessed: ${results.length} files`, 'reset');
  log(`Successful: ${successful.length}`, 'green');
  
  if (failed.length > 0) {
    log(`Failed: ${failed.length}`, 'red');
  }

  log(`\nTotal saved: ${formatBytes(totalSaved)}`, 'green');

  // Print table
  log('\nFile Details:', 'blue');
  log('─'.repeat(60), 'reset');
  log(
    'File'.padEnd(30) +
    'Before'.padEnd(12) +
    'After'.padEnd(12) +
    'Saved',
    'reset'
  );
  log('─'.repeat(60), 'reset');

  for (const result of successful) {
    log(
      result.filename.substring(0, 28).padEnd(30) +
      formatBytes(result.inputSize).padEnd(12) +
      formatBytes(result.outputSize).padEnd(12) +
      `${result.percent}%`,
      'reset'
    );
  }

  log('─'.repeat(60), 'reset');
  log('\nOptimization complete!\n', 'green');
}

// ===========================================
// Run
// ===========================================

optimizeModels().catch((error) => {
  log(`\nFatal error: ${error.message}`, 'red');
  process.exit(1);
});
