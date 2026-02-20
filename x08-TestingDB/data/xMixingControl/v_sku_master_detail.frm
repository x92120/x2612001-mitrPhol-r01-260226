TYPE=VIEW
query=select `sm`.`id` AS `id`,`sm`.`sku_id` AS `sku_id`,`sm`.`sku_name` AS `sku_name`,`sm`.`std_batch_size` AS `std_batch_size`,`sm`.`uom` AS `uom`,`sm`.`status` AS `status`,`sm`.`creat_by` AS `creat_by`,`sm`.`created_at` AS `created_at`,`sm`.`update_by` AS `update_by`,`sm`.`updated_at` AS `updated_at`,count(distinct `ss`.`phase_number`) AS `total_phases`,count(`ss`.`id`) AS `total_sub_steps`,max(`ss`.`updated_at`) AS `last_step_update` from (`xmixingcontrol`.`sku_masters` `sm` left join `xmixingcontrol`.`sku_steps` `ss` on(`sm`.`sku_id` = `ss`.`sku_id`)) group by `sm`.`id`,`sm`.`sku_id`,`sm`.`sku_name`,`sm`.`std_batch_size`,`sm`.`uom`,`sm`.`status`,`sm`.`creat_by`,`sm`.`created_at`,`sm`.`update_by`,`sm`.`updated_at`
md5=b96d1d3463d1b3344e23cf08b646a7a2
updatable=0
algorithm=0
definer_user=mixingcontrol
definer_host=%
suid=1
with_check_option=0
timestamp=0001771501842973891
create-version=2
source=select `sm`.`id` AS `id`,`sm`.`sku_id` AS `sku_id`,`sm`.`sku_name` AS `sku_name`,`sm`.`std_batch_size` AS `std_batch_size`,`sm`.`uom` AS `uom`,`sm`.`status` AS `status`,`sm`.`creat_by` AS `creat_by`,`sm`.`created_at` AS `created_at`,`sm`.`update_by` AS `update_by`,`sm`.`updated_at` AS `updated_at`,count(distinct `ss`.`phase_number`) AS `total_phases`,count(`ss`.`id`) AS `total_sub_steps`,max(`ss`.`updated_at`) AS `last_step_update` from (`sku_masters` `sm` left join `sku_steps` `ss` on((`sm`.`sku_id` = `ss`.`sku_id`))) group by `sm`.`id`,`sm`.`sku_id`,`sm`.`sku_name`,`sm`.`std_batch_size`,`sm`.`uom`,`sm`.`status`,`sm`.`creat_by`,`sm`.`created_at`,`sm`.`update_by`,`sm`.`updated_at`
client_cs_name=utf8mb4
connection_cl_name=utf8mb4_0900_ai_ci
view_body_utf8=select `sm`.`id` AS `id`,`sm`.`sku_id` AS `sku_id`,`sm`.`sku_name` AS `sku_name`,`sm`.`std_batch_size` AS `std_batch_size`,`sm`.`uom` AS `uom`,`sm`.`status` AS `status`,`sm`.`creat_by` AS `creat_by`,`sm`.`created_at` AS `created_at`,`sm`.`update_by` AS `update_by`,`sm`.`updated_at` AS `updated_at`,count(distinct `ss`.`phase_number`) AS `total_phases`,count(`ss`.`id`) AS `total_sub_steps`,max(`ss`.`updated_at`) AS `last_step_update` from (`xmixingcontrol`.`sku_masters` `sm` left join `xmixingcontrol`.`sku_steps` `ss` on(`sm`.`sku_id` = `ss`.`sku_id`)) group by `sm`.`id`,`sm`.`sku_id`,`sm`.`sku_name`,`sm`.`std_batch_size`,`sm`.`uom`,`sm`.`status`,`sm`.`creat_by`,`sm`.`created_at`,`sm`.`update_by`,`sm`.`updated_at`
mariadb-version=120202
