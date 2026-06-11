/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { HttpResourceRef } from "@angular/common/http";
import { computed, Signal, signal } from "@angular/core";
import { PiResponse } from "@app/app.component";
import { AdminRealms, Realm, Realms, RealmServiceInterface } from "@services/realm/realm.service";
import { of } from "rxjs";
import { MockHttpResourceRef, MockPiResponse } from "./mock-utils";

export class MockRealmService implements RealmServiceInterface {
  realms = signal<Realms>({});
  adminRealmResource: HttpResourceRef<PiResponse<AdminRealms, unknown> | undefined> = new MockHttpResourceRef(
    MockPiResponse.fromValue([])
  );
  adminRealmOptions = signal<string[]>([]);
  selectedRealms = signal<string[]>([]);

  realmResource = new MockHttpResourceRef<PiResponse<Realms> | undefined>(MockPiResponse.fromValue<Realms>({}));

  realmOptions = signal<string[]>([]);

  defaultRealmResource = new MockHttpResourceRef<PiResponse<Realms> | undefined>(
    MockPiResponse.fromValue<Realms>({
      realm1: { default: true, id: 1, option: "", resolver: [] }
    })
  );

  defaultRealm: Signal<string> = computed(() => {
    const data = this.defaultRealmResource.value()?.result?.value;
    return data ? (Object.keys(data)[0] ?? "") : "";
  });

  createRealm = jest
    .fn()
    .mockImplementation((realm: string, nodeId: string, resolvers: { name: string; priority?: number | null }[]) => {
      const current: Realms = this.realmResource.value()?.result?.value ?? {};
      const existing: Realm | undefined = current[realm];

      const newResolverEntries = resolvers.map((r) => ({
        name: r.name,
        node: nodeId,
        type: "mock",
        priority: r.priority ?? null
      }));

      const updatedRealm: Realm = existing
        ? { ...existing, resolver: [...(existing.resolver ?? []), ...newResolverEntries] }
        : { default: false, id: Object.keys(current).length + 1, option: "", resolver: newResolverEntries };

      const updatedRealms: Realms = { ...current, [realm]: updatedRealm };
      this.realmResource.set(MockPiResponse.fromValue<Realms>(updatedRealms));
      return of(MockPiResponse.fromValue<{ realm: string; nodeId: string; resolvers: typeof resolvers }>({
        realm,
        nodeId,
        resolvers
      }));
    });

  deleteRealm = jest.fn().mockImplementation((realm: string) => {
    const current: Realms = this.realmResource.value()?.result?.value ?? {};
    if (current[realm]) {
      const rest = { ...current };
      delete rest[realm];
      this.realmResource.set(MockPiResponse.fromValue<Realms>(rest));
    }
    return of(MockPiResponse.fromValue<number>(1));
  });

  setDefaultRealm = jest.fn().mockImplementation((realm: string) => {
    const current: Realms = this.realmResource.value()?.result?.value ?? {};
    const next: Realms = Object.fromEntries(
      Object.entries(current).map(([key, value]) => [key, { ...value, default: key === realm }])
    );

    this.realmResource.set(MockPiResponse.fromValue<Realms>(next));

    this.defaultRealmResource.set(
      MockPiResponse.fromValue<Realms>({
        [realm]: next[realm] ?? { default: true, id: 1, option: "", resolver: [] }
      })
    );

    return of(MockPiResponse.fromValue<number>(1));
  });
}
