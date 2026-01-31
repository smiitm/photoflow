import { getProject } from "@/lib/api";
import { notFound } from "next/navigation";
import { Uploader } from "./uploader";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

export default async function ProjectPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const resolvedParams = await params;
  let project;
  try {
    project = await getProject(resolvedParams.id);
  } catch (e) {
    notFound();
  }

  return (
    <div className="container max-w-screen-xl py-8 px-4 mx-auto space-y-8 flex-1 flex flex-col">
      <div className="flex items-center gap-4">
        <Button variant="outline" size="icon" asChild>
          <Link href="/">
            <ArrowLeft className="h-4 w-4" />
            <span className="sr-only">Back to Projects</span>
          </Link>
        </Button>
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{project.name}</h1>
          <p className="text-muted-foreground">ID: {project.id} • {project.image_count} Images</p>
        </div>
      </div>

      <div className="flex-1 flex flex-col">
        <Uploader projectId={project.id} />
      </div>
    </div>
  );
}
