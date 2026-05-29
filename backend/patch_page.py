import sys
import re

with open('frontend/app/practice/[session_id]/upgrade/page.tsx', 'r') as f:
    content = f.read()

# 1. Update SmartGapCard signature and usage to pass existingEntities
content = content.replace(
    '''function SmartGapCard({
  index,
  gap,
  answer,
  onChange,
}: {
  index: number;
  gap: string;
  answer: GapAnswer;
  onChange: (index: number, answer: GapAnswer) => void;
}) {''',
    '''function SmartGapCard({
  index,
  gap,
  answer,
  onChange,
  existingEntities = [],
}: {
  index: number;
  gap: string;
  answer: GapAnswer;
  onChange: (index: number, answer: GapAnswer) => void;
  existingEntities?: string[];
}) {'''
)

# 2. Replace the input with a dropdown in SmartGapCard
old_input = '''<input
                      type="text"
                      value={answer.attachToExisting || ""}
                      onChange={(e) => update({ attachToExisting: e.target.value })}
                      placeholder="e.g. My E-Commerce project, or TechCorp internship…"
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-indigo-500 transition-colors"
                    />'''

new_input = '''{existingEntities && existingEntities.length > 0 ? (
                      <div className="space-y-2">
                        <select
                          value={existingEntities.includes(answer.attachToExisting || "") ? answer.attachToExisting : (answer.attachToExisting ? "Other..." : "")}
                          onChange={(e) => {
                            if (e.target.value === "Other...") {
                              update({ attachToExisting: " " }); // triggers fallback
                            } else {
                              update({ attachToExisting: e.target.value });
                            }
                          }}
                          className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-zinc-200 focus:outline-none focus:border-indigo-500 transition-colors"
                        >
                          <option value="" disabled>Select an existing project or job...</option>
                          {existingEntities.map((ent, idx) => (
                            <option key={idx} value={ent}>{ent}</option>
                          ))}
                          <option value="Other...">Other...</option>
                        </select>
                        {(!existingEntities.includes(answer.attachToExisting || "") && answer.attachToExisting) && (
                          <input
                            type="text"
                            value={answer.attachToExisting === " " ? "" : answer.attachToExisting}
                            onChange={(e) => update({ attachToExisting: e.target.value })}
                            placeholder="Type the name..."
                            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-indigo-500 transition-colors mt-2"
                          />
                        )}
                      </div>
                    ) : (
                      <input
                        type="text"
                        value={answer.attachToExisting || ""}
                        onChange={(e) => update({ attachToExisting: e.target.value })}
                        placeholder="e.g. My E-Commerce project, or TechCorp internship…"
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-indigo-500 transition-colors"
                      />
                    )}'''

content = content.replace(old_input, new_input)

# 3. Replace ImprovementsList with OptimizationsList logic
old_improvements = '''function ImprovementsList({
  improvements,
  selected,
  onToggle,
}: {
  improvements: string[];
  selected: Set<number>;
  onToggle: (index: number) => void;
}) {'''

new_improvements = '''function OptimizationsList({
  optimizeProjects,
  setOptimizeProjects,
  optimizeExperience,
  setOptimizeExperience,
  optimizeSummary,
  setOptimizeSummary,
}: {
  optimizeProjects: boolean;
  setOptimizeProjects: (v: boolean) => void;
  optimizeExperience: boolean;
  setOptimizeExperience: (v: boolean) => void;
  optimizeSummary: boolean;
  setOptimizeSummary: (v: boolean) => void;
}) {
  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <div>
          <h2 className="text-zinc-100 font-semibold text-base">Terminology Improvements</h2>
          <p className="text-zinc-500 text-xs mt-0.5">
            Allow our AI to rewrite sections of your resume to naturally incorporate JD keywords.
          </p>
        </div>
      </div>
      <div className="space-y-2">
        <label className={`flex items-start gap-3 rounded-xl p-4 cursor-pointer border transition-colors ${optimizeProjects ? "bg-indigo-600/10 border-indigo-500/40" : "bg-slate-800/50 border-slate-700 hover:border-indigo-500/30"}`}>
          <input type="checkbox" checked={optimizeProjects} onChange={(e) => setOptimizeProjects(e.target.checked)} className="mt-0.5 accent-indigo-500 shrink-0 w-4 h-4" />
          <div className="flex-1 min-w-0">
            <span className="text-zinc-300 text-sm leading-relaxed block">Optimize wording in your <b>Projects</b> section</span>
          </div>
        </label>
        <label className={`flex items-start gap-3 rounded-xl p-4 cursor-pointer border transition-colors ${optimizeExperience ? "bg-indigo-600/10 border-indigo-500/40" : "bg-slate-800/50 border-slate-700 hover:border-indigo-500/30"}`}>
          <input type="checkbox" checked={optimizeExperience} onChange={(e) => setOptimizeExperience(e.target.checked)} className="mt-0.5 accent-indigo-500 shrink-0 w-4 h-4" />
          <div className="flex-1 min-w-0">
            <span className="text-zinc-300 text-sm leading-relaxed block">Optimize wording in your <b>Experience</b> section</span>
          </div>
        </label>
        <label className={`flex items-start gap-3 rounded-xl p-4 cursor-pointer border transition-colors ${optimizeSummary ? "bg-indigo-600/10 border-indigo-500/40" : "bg-slate-800/50 border-slate-700 hover:border-indigo-500/30"}`}>
          <input type="checkbox" checked={optimizeSummary} onChange={(e) => setOptimizeSummary(e.target.checked)} className="mt-0.5 accent-indigo-500 shrink-0 w-4 h-4" />
          <div className="flex-1 min-w-0">
            <span className="text-zinc-300 text-sm leading-relaxed block">Optimize wording in your <b>Professional Summary</b></span>
          </div>
        </label>
      </div>
    </div>
  );
}

// Dummy ImprovementsList to prevent syntax errors if referenced elsewhere (we remove its usage below)
function ImprovementsList_Old(a: any) { return null; }'''

content = content.replace(old_improvements, new_improvements)

# 4. Add state to default export
state_add = '''
  // Step 1 state — structured gap answers (skill knowledge only)
  const [gapAnswers, setGapAnswers] = useState<Record<number, GapAnswer>>({});
  // Standalone top-level experience and project entries
  const [standaloneExperiences, setStandaloneExperiences] = useState<ExperienceEntry[]>([]);
  const [standaloneProjects, setStandaloneProjects] = useState<ProjectEntry[]>([]);
  const [selectedImprovements, setSelectedImprovements] = useState<Set<number>>(new Set());
  const [optimizeProjects, setOptimizeProjects] = useState(false);
  const [optimizeExperience, setOptimizeExperience] = useState(false);
  const [optimizeSummary, setOptimizeSummary] = useState(false);
  const [customAdditions, setCustomAdditions] = useState("");
'''

content = re.sub(r'// Step 1 state .*?\n.*?\n.*?\n.*?\n.*?setCustomAdditions', state_add, content, flags=re.DOTALL)

# 5. Fix refine call and pass flags
old_refine_call = '''const result = await refineWithGaps(
        session_id,
        combinedCustom,
        gapSelections,
        selectedImprovementStrings
      );'''

new_refine_call = '''const result = await refineWithGaps(
        session_id,
        combinedCustom,
        gapSelections,
        selectedImprovementStrings,
        false,
        {
          projects: optimizeProjects,
          experience: optimizeExperience,
          summary: optimizeSummary
        }
      );'''
content = content.replace(old_refine_call, new_refine_call)

# Ensure early return also handles optimization flags properly
old_early = '''if (Object.keys(gapSelections).length === 0 && combinedCustom.trim() === "" && selectedImprovementStrings.length === 0) {'''
new_early = '''if (Object.keys(gapSelections).length === 0 && combinedCustom.trim() === "" && selectedImprovementStrings.length === 0 && !optimizeProjects && !optimizeExperience && !optimizeSummary) {'''
content = content.replace(old_early, new_early)

# 6. Replace ImprovementsList usage with OptimizationsList
old_usage = '''<ImprovementsList improvements={session.enhanced_analysis?.improvements || []} selected={selectedImprovements} onToggle={handleToggleImprovement} />'''
new_usage = '''<OptimizationsList 
                    optimizeProjects={optimizeProjects} setOptimizeProjects={setOptimizeProjects}
                    optimizeExperience={optimizeExperience} setOptimizeExperience={setOptimizeExperience}
                    optimizeSummary={optimizeSummary} setOptimizeSummary={setOptimizeSummary}
                  />'''
content = content.replace(old_usage, new_usage)

# Update SmartGapCard usage
old_sgc_usage = '''<SmartGapCard
                        key={i}
                        index={i}
                        gap={gap}
                        answer={gapAnswers[i]}
                        onChange={handleGapAnswerChange}
                      />'''
new_sgc_usage = '''<SmartGapCard
                        key={i}
                        index={i}
                        gap={gap}
                        answer={gapAnswers[i]}
                        onChange={handleGapAnswerChange}
                        existingEntities={session.enhanced_analysis?.existing_entities || []}
                      />'''
content = content.replace(old_sgc_usage, new_sgc_usage)

# 7. Update RefinedItemCard to handle rewrites
old_ric = '''else if (item.startsWith("project:")) {
    const content = item.replace("project:", "").trim();
    const nameMatch = content.match(/^(.*?)—/);
    title = nameMatch ? nameMatch[1].trim() : "New Project";
    icon = <FolderPlus size={16} className="text-indigo-400" />;
    typeLabel = "Project";
  }'''

new_ric = '''else if (item.startsWith("project:")) {
    const content = item.replace("project:", "").trim();
    const nameMatch = content.match(/^(.*?)—/);
    title = nameMatch ? nameMatch[1].trim() : "New Project";
    icon = <FolderPlus size={16} className="text-indigo-400" />;
    typeLabel = "Project";
  } else if (item.startsWith("rewrite_project:")) {
    const content = item.replace("rewrite_project:", "").trim();
    const nameMatch = content.match(/^(.*?)—/);
    title = nameMatch ? nameMatch[1].trim() : "Rewritten Project";
    icon = <FolderPlus size={16} className="text-indigo-400" />;
    typeLabel = "Rewritten Project";
  } else if (item.startsWith("rewrite_experience:")) {
    const content = item.replace("rewrite_experience:", "").trim();
    const parts = content.split("|").map(s => s.trim());
    title = parts[0] || "Rewritten Experience";
    icon = <Briefcase size={16} className="text-indigo-400" />;
    typeLabel = "Rewritten Experience";
  } else if (item.startsWith("rewrite_summary:")) {
    title = "Professional Summary";
    icon = <FileText size={16} className="text-indigo-400" />;
    typeLabel = "Rewritten Summary";
  }'''

content = content.replace(old_ric, new_ric)

with open('frontend/app/practice/[session_id]/upgrade/page.tsx', 'w') as f:
    f.write(content)
print("page.tsx patched successfully!")
