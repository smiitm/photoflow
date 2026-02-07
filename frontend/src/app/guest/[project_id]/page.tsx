import { getProject } from "@/lib/api";
import { notFound } from "next/navigation";
import { GuestPortal } from "@/components/guest-portal";

export default async function GuestPage({
  params,
}: {
  params: Promise<{ project_id: string }>;
}) {
  const resolvedParams = await params;
  let project;
  try {
    project = await getProject(resolvedParams.project_id);
  } catch (e) {
    notFound();
  }

  return (
    <div className="container max-w-screen-xl py-10 px-4 mx-auto flex-1 flex flex-col">
      <div className="text-center mb-10">
        <h1 className="text-4xl font-extrabold tracking-tight mb-4">{project.name}</h1>
        <p className="text-lg text-muted-foreground">
          Upload a selfie to instantly find all your photos from the event.
        </p>
      </div>

      <GuestPortal projectId={project.id} />
    </div>
  );
}
