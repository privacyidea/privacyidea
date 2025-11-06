import { signal, computed, Signal, WritableSignal } from "@angular/core";
import { of } from "rxjs";
import { Resolver, ResolverServiceInterface } from "../../app/services/resolver/resolver.service";
import { PiResponse } from "../../app/app.component";

export class MockResolverService implements ResolverServiceInterface {
  selectedResolverName: WritableSignal<string> = signal("");

  private _resolversValue: WritableSignal<Resolver[]> = signal([]);
  resolvers: Signal<Resolver[]> = this._resolversValue.asReadonly();

  private _resolverOptionsValue: WritableSignal<string[]> = signal([]);
  resolverOptions: Signal<string[]> = this._resolverOptionsValue.asReadonly();

  postResolverTest = jest.fn().mockReturnValue(of({} as PiResponse<any>));
  postResolver = jest.fn().mockReturnValue(of({} as PiResponse<any>));
  deleteResolver = jest.fn().mockReturnValue(of({} as PiResponse<any>));

  setResolvers(data: Resolver[]): void {
    this._resolversValue.set(data);
  }

  setResolverOptions(options: string[]): void {
    this._resolverOptionsValue.set(options);
  }
}
