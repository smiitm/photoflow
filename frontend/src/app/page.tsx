import { getProjects } from "@/lib/api";
import { CreateProjectDialog } from "@/components/create-project-dialog";
import { ProjectCard } from "@/components/project-card";

export default async function Home() {
  let projects: any[] = [];
  try {
    projects = await getProjects();
  } catch (error) {
    console.error("Failed to load projects:", error);
  }

  return (
    <div className="container max-w-screen-xl py-10 px-4 mx-auto space-y-8 flex-1">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Projects</h1>
          <p className="text-muted-foreground">Manage your event photo galleries.</p>
        </div>
        <CreateProjectDialog />
      </div>

      {projects.length === 0 ? (
        <div className="flex flex-col items-center justify-center p-20 text-center border rounded-lg border-dashed">
          <h2 className="text-xl font-semibold">No projects found</h2>
          <p className="text-muted-foreground mt-2 mb-6">Create a new project to start uploading photos.</p>
          <CreateProjectDialog />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {projects.map((project: any) => (
            <ProjectCard key={project.id} project={project} />
          ))}
        </div>
      )}
    </div>
  );
}
