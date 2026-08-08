-- ========================================================
-- SCRIPT AUTO-SETUP STORAGE BUCKET VA POLICY TREN SUPABASE
-- Chạy script này tại Supabase -> SQL Editor -> Run
-- ========================================================

-- 1. Tạo Storage Bucket 'pnx-userdata' và để chế độ Public
INSERT INTO storage.buckets (id, name, public)
VALUES ('pnx-userdata', 'pnx-userdata', true)
ON CONFLICT (id) DO UPDATE SET public = true;

-- 2. Xóa Policy cũ (nếu có) để tránh xung đột
DROP POLICY IF EXISTS "Allow All Storage pnx-userdata" ON storage.objects;

-- 3. Tạo Policy cho phép ĐỌC, GHI, SỬA, XÓA hoàn toàn tự do trên bucket 'pnx-userdata'
CREATE POLICY "Allow All Storage pnx-userdata"
ON storage.objects
FOR ALL
TO public
USING (bucket_id = 'pnx-userdata')
WITH CHECK (bucket_id = 'pnx-userdata');
