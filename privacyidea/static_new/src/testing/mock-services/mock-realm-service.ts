/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { computed, Signal, signal, WritableSignal } from "@angular/core";
import { of } from "rxjs";
import { Realm, Realms, RealmServiceInterface } from "../../app/services/realm/realm.service";
import { PiResponse } from "../../app/app.component";
import { MockHttpResourceRef, MockPiResponse } from "./mock-utils";

export class MockRealmService implements RealmServiceInterface {
  selectedRealms = signal<string[]>([]);

  realmResource = new MockHttpResourceRef<PiResponse<Realms> | undefined>(
    MockPiResponse.fromValue<Realms>({} as any)
  );

  realmOptions: Signal<string[]> = computed(() => {
    const realms = this.realmResource.value()?.result?.value as any;
    return realms ? Object.keys(realms) : [];
  });

  defaultRealmResource = new MockHttpResourceRef<PiResponse<Realms> | undefined>(
    MockPiResponse.fromValue<Realms>({
      realm1: { default: true, id: 1, option: "", resolver: [] } as Realm
    } as any)
  );

  defaultRealm: Signal<string> = computed(() => {
    const data = this.defaultRealmResource.value()?.result?.value as any;
    return data ? Object.keys(data)[0] : "";
  });

  createRealm = jest.fn().mockImplementation((realm: string, nodeId: string, resolvers: { name: string; priority?: number | null }[]) => {
    const current = (this.realmResource.value()?.result?.value as any) ?? {};
    const existing: Realm | undefined = current[realm];

    const newResolverEntries = resolvers.map((r) => ({ name: r.name, node: nodeId, type: "mock", priority: r.priority ?? null }));

    const updatedRealm: Realm = existing
      ? { ...existing, resolver: [...(existing.resolver ?? []), ...newResolverEntries] }
      : { default: false, id: Object.keys(current).length + 1, option: "", resolver: newResolverEntries } as Realm;

    const updatedRealms = { ...current, [realm]: updatedRealm };
    (this.realmResource as MockHttpResourceRef<PiResponse<Realms> | undefined>).set(
      MockPiResponse.fromValue<Realms>(updatedRealms as any)
    );
    return of(MockPiResponse.fromValue<any>({ realm, nodeId, resolvers }));
  });

  deleteRealm = jest.fn().mockImplementation((realm: string) => {
    const current = (this.realmResource.value()?.result?.value as any) ?? {};
    if (current[realm]) {
      const { [realm]: _, ...rest } = current;
      (this.realmResource as MockHttpResourceRef<PiResponse<Realms> | undefined>).set(
        MockPiResponse.fromValue<Realms>(rest as any)
      );
    }
    return of(MockPiResponse.fromValue<number>(1));
  });

  setDefaultRealm = jest.fn().mockImplementation((realm: string) => {
    const current = (this.realmResource.value()?.result?.value as any) ?? {};

    Object.keys(current).forEach((key) => {
      current[key] = { ...(current[key] as Realm), default: key === realm };
    });

    (this.realmResource as MockHttpResourceRef<PiResponse<Realms> | undefined>).set(
      MockPiResponse.fromValue<Realms>(current as any)
    );

    (this.defaultRealmResource as MockHttpResourceRef<PiResponse<Realms> | undefined>).set(
      MockPiResponse.fromValue<Realms>({
        [realm]:
          current[realm] ?? ({ default: true, id: 1, option: "", resolver: [] } as Realm)
      } as any)
    );

    return of(MockPiResponse.fromValue<number>(1));
  });
}
