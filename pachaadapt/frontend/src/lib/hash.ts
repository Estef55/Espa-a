/** SHA-256 en hexadecimal con Web Crypto. Devuelve null si el contexto no lo permite (p. ej. http en red local). */
export async function sha256Hex(file:Blob):Promise<string|null>{
  const subtle=globalThis.crypto?.subtle;
  if(!subtle)return null;
  try{
    const digest=await subtle.digest("SHA-256",await file.arrayBuffer());
    return Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,"0")).join("");
  }catch{return null;}
}
