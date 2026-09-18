import type { CampaignRecord, HomebrewItem, ReferenceItem } from './types'

export type EnemyGroup = {resource_id:string;quantity:number;wave:number}
export type AdventureResource = HomebrewItem | ReferenceItem
export type AdventureTemplate = {id:string;title:string;terrain:string;level_hint:string;description:string;situation_id:string;temple_id:string;minigame_id:string|null;enemy_groups:EnemyGroup[]}
export type AdventureBudget = {rules:string;levels:number[];party_source:string;thresholds:number[];waves:{wave:number;count:number;xp:number;adjusted_xp:number;multiplier:number;difficulty:string}[];total_xp:number;warnings:string[]}
export type AdventureStep = {kind:string;title:string;description:string;resource?:AdventureResource;completed_at?:string;check_results?:{name:string;d20:number;modifier:number;total:number;dc:number;success:boolean;manual:boolean;created_at:string}[]}
export type Adventure = Omit<CampaignRecord,'data'> & {data:{revision:number;current_step:number;steps:AdventureStep[];enemy_groups:(EnemyGroup & {resource:AdventureResource})[];budget:AdventureBudget;hex_id:string|null;location_id:string|null;alert_delta:number;released_waves:number[];combat_id?:string;notes:{text:string;step:string;created_at:string}[]}}
export type AdventureDraft = {campaign_id:string;title:string;description:string;hex_id:string|null;location_id:string|null;situation_id:string|null;temple_id:string|null;minigame_id:string|null;enemy_groups:EnemyGroup[];alert_delta:number;include_characters:boolean}
