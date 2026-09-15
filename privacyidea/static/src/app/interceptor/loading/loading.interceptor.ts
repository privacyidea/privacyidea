/**
 * (c) NetKnights GmbH 2026,  https://netknights.it
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
import { HttpInterceptorFn } from "@angular/common/http";
import { inject } from "@angular/core";
import { LoadingService, LoadingServiceInterface } from "@services/loading/loading-service";
import { finalize, shareReplay } from "rxjs/operators";
import { v4 as uuid } from "uuid";

export const loadingInterceptor: HttpInterceptorFn = (req, next) => {
  const loadingService: LoadingServiceInterface = inject(LoadingService);

  const loadingId = uuid();

  // Registered up front rather than by subscribing to the request ourselves: a caller that unsubscribes early -
  // switching a dashboard preset before its request answers, say - has to actually cancel the underlying HTTP call,
  // and a second, independent subscription of our own here would keep shareReplay's refCount above zero (and the
  // request running) long after the caller has walked away. finalize below runs on every subscriber's own teardown,
  // early or not, which is what removeLoading is keyed to instead.
  loadingService.addLoading(loadingId, req.url);

  // shareReplay still earns its place beyond the loading count: it is what lets two callers subscribing to the same
  // request share one HTTP call rather than firing it twice.
  return next(req).pipe(
    shareReplay({ bufferSize: 1, refCount: true }),
    finalize(() => loadingService.removeLoading(loadingId))
  );
};
