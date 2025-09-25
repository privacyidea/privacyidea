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
import { HttpInterceptorFn } from "@angular/common/http";
import { inject } from "@angular/core";
import { finalize, share } from "rxjs/operators";
import { v4 as uuid } from "uuid";
import { LoadingService, LoadingServiceInterface } from "../../services/loading/loading-service";

export const loadingInterceptor: HttpInterceptorFn = (req, next) => {
  const loadingService: LoadingServiceInterface = inject(LoadingService);

  const loadingId = uuid();

  const sharedRequest$ = next(req).pipe(
    share(),
    finalize(() => {
      loadingService.removeLoading(loadingId);
    })
  );
  loadingService.addLoading({
    key: loadingId,
    observable: sharedRequest$,
    url: req.url
  });

  return sharedRequest$;
};
