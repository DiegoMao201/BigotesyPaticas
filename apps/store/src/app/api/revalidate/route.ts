import { revalidatePath, revalidateTag } from 'next/cache';

export async function POST(request: Request) {
  const auth = request.headers.get('authorization');
  if (auth !== `Bearer ${process.env.REVALIDATE_TOKEN}`) {
    return Response.json({ error: 'unauthorized' }, { status: 401 });
  }

  const body = await request.json();
  const { path, paths, tag } = body as {
    path?: string;
    paths?: string[];
    tag?: string;
  };

  if (path) revalidatePath(path);
  if (paths && Array.isArray(paths)) {
    paths.filter(Boolean).forEach((p) => revalidatePath(p));
  }
  if (tag) revalidateTag(tag);

  return Response.json({
    revalidated: true,
    now: Date.now(),
    cleared: path ?? paths ?? tag ?? null,
  });
}
