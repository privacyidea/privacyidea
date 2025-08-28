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
