/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * This code is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 **/
import { TestBed } from "@angular/core/testing";
import { HttpEvent, HttpRequest, HttpResponse } from "@angular/common/http";
import { Observable, of, Subject } from "rxjs";
import { loadingInterceptor } from "./loading.interceptor";
import { LoadingService } from "../../services/loading/loading-service";
import { MockLoadingService } from "../../../testing/mock-services";

jest.mock("uuid", () => ({ v4: jest.fn(() => "mock-uuid") }));

describe("loadingInterceptor", () => {
  let loadingSvc: MockLoadingService;

  const run = (req: HttpRequest<any>, next: (req: HttpRequest<any>) => Observable<HttpEvent<any>>) =>
    TestBed.runInInjectionContext(() => loadingInterceptor(req, next));

  beforeEach(() => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [{ provide: LoadingService, useClass: MockLoadingService }]
    });

    loadingSvc = TestBed.inject(LoadingService) as unknown as MockLoadingService;
  });

  it("is creatable", () => {
    const req = new HttpRequest("GET", "/api/x");
    const next = jest.fn().mockReturnValue(of(new HttpResponse({ status: 200 })));
    const shared$ = run(req, next);
    expect(shared$).toBeTruthy();
  });

  it("calls addLoading with uuid, url and the returned shared observable", () => {
    const req = new HttpRequest("GET", "/api/items");
    const src$ = new Subject<HttpEvent<any>>();
    const next = jest.fn().mockReturnValue(src$.asObservable());

    const shared$ = run(req, next);

    expect(next).toHaveBeenCalledTimes(1);
    expect(loadingSvc.addLoading).toHaveBeenCalledTimes(1);

    const arg = loadingSvc.addLoading.mock.calls[0][0];
    expect(arg.key).toBe("mock-uuid");
    expect(arg.url).toBe("/api/items");
    expect(arg.observable).toBe(shared$);
  });

  it("removes loading on completion (finalize)", () => {
    const req = new HttpRequest("GET", "/done");
    const src$ = new Subject<HttpEvent<any>>();
    const next = jest.fn().mockReturnValue(src$.asObservable());

    const shared$ = run(req, next);

    const results: HttpEvent<any>[] = [];
    shared$.subscribe((e) => results.push(e));

    const ev = new HttpResponse({ status: 200, body: "ok" });
    src$.next(ev);
    src$.complete();

    expect(results).toEqual([ev]);
    expect(loadingSvc.removeLoading).toHaveBeenCalledWith("mock-uuid");
    expect(loadingSvc.removeLoading).toHaveBeenCalledTimes(1);
  });

  it("removes loading on error (finalize)", () => {
    const req = new HttpRequest("GET", "/fail");
    const src$ = new Subject<HttpEvent<any>>();
    const next = jest.fn().mockReturnValue(src$.asObservable());

    const shared$ = run(req, next);

    const errors: any[] = [];
    shared$.subscribe({
      error: (e) => errors.push(e)
    });

    const err = new Error("boom");
    src$.error(err);

    expect(errors[0]).toBe(err);
    expect(loadingSvc.removeLoading).toHaveBeenCalledWith("mock-uuid");
    expect(loadingSvc.removeLoading).toHaveBeenCalledTimes(1);
  });

  it("shares the underlying source across overlapping subscribers", () => {
    const req = new HttpRequest("GET", "/overlap");
    const src$ = new Subject<HttpEvent<any>>();
    const next = jest.fn().mockReturnValue(src$.asObservable());

    const shared$ = run(req, next);

    const a: HttpEvent<any>[] = [];
    const b: HttpEvent<any>[] = [];
    const subA = shared$.subscribe((e) => a.push(e));
    const subB = shared$.subscribe((e) => b.push(e));

    const ev = new HttpResponse({ status: 200, body: "x" });
    src$.next(ev);
    src$.complete();

    subA.unsubscribe();
    subB.unsubscribe();

    expect(next).toHaveBeenCalledTimes(1); // single subscription to source
    expect(a).toEqual([ev]);
    expect(b).toEqual([ev]);
    // finalize runs per subscription after share(), so two calls here
    expect(loadingSvc.removeLoading).toHaveBeenCalledTimes(2);
  });
});